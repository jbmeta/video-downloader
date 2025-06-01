from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import re
import os
import threading
import json # For debugging, if you uncomment print(json.dumps(info...))

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
# Create the downloads directory if it doesn't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    """Serves the main HTML page."""
    return app.send_static_file('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serves static files (CSS, JS)."""
    return app.send_static_file(path)

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    """
    Receives a Twitter/X tweet URL, extracts video information using yt-dlp,
    and returns available video formats/resolutions.
    """
    tweet_url = request.json.get('tweet_url')

    # Basic URL validation for Twitter/X tweet links
    # Updated regex to accept both twitter.com and x.com
    if not re.match(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+", tweet_url):
        return jsonify({"error": "Invalid Twitter/X URL. Please provide a direct link to a tweet (e.g., https://x.com/user/status/123...)."}), 400

    try:
        ydl_opts = {
            'quiet': True,           # Suppress yt-dlp console output
            'no_warnings': True,     # Suppress yt-dlp warnings
            'skip_download': True,   # Only extract info, don't download yet
            'force_generic_extractor': True, # Helps ensure it processes the URL
            # Request best video and best audio, yt-dlp will mux them if needed
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            # Specific argument for Twitter HLS streams, often resolves issues
            'extractor_args': {'twitter': {'skip_hls_ts': True}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tweet_url, download=False)
            
            # --- DEBUGGING AID: Uncomment to print full info dictionary to console ---
            # print(json.dumps(info, indent=4))
            # -------------------------------------------------------------------------

            if 'formats' not in info:
                return jsonify({"error": "No video found in this tweet or no downloadable formats recognized."}), 404

            video_formats_options = []
            seen_resolutions = set()

            # Iterate through all available formats to find suitable video streams for display
            for f in info.get('formats', []):
                # Filter for MP4 video streams that have a video codec and a defined height
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('height'):
                    resolution_str = f"{f.get('width')}x{f.get('height')}" if f.get('width') and f.get('height') else f.get('resolution')

                    if resolution_str and resolution_str not in seen_resolutions:
                        video_formats_options.append({
                            "url": f['url'], # This might be an HLS manifest, yt-dlp handles it
                            "resolution": resolution_str,
                            "filesize": f.get('filesize_approx') or f.get('filesize') # Prioritize approximate size
                        })
                        seen_resolutions.add(resolution_str)
            
            # Also consider formats that yt-dlp has specifically 'requested' or processed
            for rf in info.get('requested_formats', []):
                if rf.get('ext') == 'mp4' and rf.get('vcodec') != 'none' and rf.get('height'):
                    resolution_str = f"{rf.get('width')}x{rf.get('height')}" if rf.get('width') and rf.get('height') else rf.get('resolution')
                    if resolution_str and resolution_str not in seen_resolutions:
                        video_formats_options.append({
                            "url": rf['url'],
                            "resolution": resolution_str,
                            "filesize": rf.get('filesize_approx') or rf.get('filesize')
                        })
                        seen_resolutions.add(resolution_str)

            if not video_formats_options:
                 return jsonify({"error": "No downloadable video formats found for this tweet."}), 404

            # Helper to extract height for sorting resolutions
            def get_height_from_resolution(res_str):
                match = re.search(r'x(\d+)', res_str) # Matches "x600" in "480x600"
                if match:
                    return int(match.group(1))
                return 0 # Default if height not found

            # Sort formats by height (highest resolution first)
            video_formats_options.sort(key=lambda x: get_height_from_resolution(x['resolution']), reverse=True)
            
            # Filter out any lingering duplicate resolutions after sorting, keeping the higher quality one
            final_video_formats = []
            added_resolutions_post_sort = set()
            for fmt in video_formats_options:
                if fmt['resolution'] not in added_resolutions_post_sort:
                    final_video_formats.append(fmt)
                    added_resolutions_post_sort.add(fmt['resolution'])


            return jsonify({"formats": final_video_formats})

    except yt_dlp.DownloadError as e:
        print(f"YT-DLP Error during info extraction: {e}")
        return jsonify({"error": f"Error extracting video information: {str(e)}. This might be a private tweet, geo-restricted, or an issue with the video."}), 500
    except Exception as e:
        print(f"General Error during info extraction: {e}")
        return jsonify({"error": "An unexpected error occurred while processing the tweet: " + str(e)}), 500

@app.route('/stream_download', methods=['POST'])
def stream_download():
    """
    Initiates the video download using yt-dlp on the server,
    and then streams the downloaded file back to the client.
    """
    video_url = request.json.get('video_url')
    resolution = request.json.get('resolution', 'unknown_resolution')
    
    # Extract tweet ID for a more meaningful filename
    tweet_id_match = re.search(r'/status/(\d+)', video_url)
    tweet_id = tweet_id_match.group(1) if tweet_id_match else 'twitter_video'

    if not video_url:
        return jsonify({"error": "Video URL missing."}), 400

    # Sanitize resolution for use in filename
    sanitized_resolution = re.sub(r'[^\w\d_]', '', resolution).replace('x', '_')
    filename_base = f"{tweet_id}_{sanitized_resolution}" # e.g., 123456789_1080p
    final_download_filename = f"{filename_base}.mp4"

    # Generate a unique temporary filename for yt-dlp to save to
    temp_filename = f"dl_temp_{os.urandom(8).hex()}_{filename_base}.mp4"
    temp_filepath = os.path.join(DOWNLOAD_DIR, temp_filename)

    try:
        # yt-dlp options for actual download and muxing
        ydl_opts = {
            'quiet': True,           # Suppress yt-dlp console output during download
            'no_warnings': True,     # Suppress yt-dlp warnings
            'outtmpl': temp_filepath, # Specify the output path for the downloaded file
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Ensure MP4 and muxing
            'merge_output_format': 'mp4', # Explicitly ensure output is MP4 if streams are separate
            'extractor_args': {'twitter': {'skip_hls_ts': True}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # yt-dlp will handle downloading from the provided URL (which could be an HLS manifest)
            # and saving it to the temporary file path. This call will block until download is complete.
            ydl.download([video_url])

        # Once downloaded, send the file back to the browser
        # This will trigger the browser's native download dialog/process
        return send_file(temp_filepath, as_attachment=True, download_name=final_download_filename)

    except yt_dlp.DownloadError as e:
        print(f"YT-DLP Error during download: {e}")
        # Clean up any partial temporary file if an error occurred
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({"error": f"Failed to download video: {str(e)}. Video might be private or an issue with the link."}), 500
    except Exception as e:
        print(f"General Error during download: {e}")
        # Clean up any partial temporary file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({"error": "An unexpected error occurred during download: " + str(e)}), 500


if __name__ == '__main__':
    # Optional: Clean up temporary files from previous runs on server startup
    print(f"Cleaning up old temporary files in {DOWNLOAD_DIR}...")
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith('dl_temp_'):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
                print(f"Removed old temp file: {f}")
            except OSError as e:
                print(f"Error removing old temp file {f}: {e}")
    
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0') # host='0.0.0.0' makes it accessible from other devices on the network