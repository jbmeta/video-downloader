from flask import Flask, request, jsonify, send_file
import yt_dlp
import re
import os
import threading
import json # Import json for detailed printing if needed

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    tweet_url = request.json.get('tweet_url')

    if not re.match(r"https?://(?:www\.)?x\.com/\w+/status/\d+", tweet_url):
        return jsonify({"error": "Invalid X URL"}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True, # We only want info here
            'force_generic_extractor': True, # Ensure it works for X
            # Request best video and best audio, yt-dlp will mux them if needed
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'extractor_args': {'x': {'skip_hls_ts': True}}, # Often helps with X HLS issues
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tweet_url, download=False)
            
            # --- DEBUGGING: Print the full info dictionary to see available formats ---
            # print(json.dumps(info, indent=4))
            # -------------------------------------------------------------------------

            if 'formats' not in info:
                return jsonify({"error": "No video found in this tweet."}), 404

            # We need to identify *combined* formats or infer them.
            # yt-dlp's 'best' formats often represent a muxed stream.
            # We'll filter based on resolution and preference for MP4.
            
            video_formats_options = []
            
            # Prioritize combined formats if available (they'll have both vcodec and acodec)
            # or formats where yt-dlp indicates it will combine.
            
            # Iterate through the formats to find suitable options.
            # For HLS streams like the one you showed, yt-dlp will typically download the .m3u8 manifest
            # and then download the video segments and combine them.
            
            # The 'best' format often represents the highest quality combined stream.
            # Let's try to extract relevant information from the 'best' or other high-quality formats.

            # Iterate through info['formats'] to find suitable video streams for display
            # We want to show options that yt-dlp *can* download and mux into MP4.
            
            # yt-dlp often creates a 'requested_formats' key if formats are merged.
            # Or we can look for formats that have both video and audio.
            
            seen_resolutions = set()

            for f in info.get('formats', []):
                # Filter for MP4 video streams, preferring those with a resolution or height/width
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('height'):
                    # Prioritize formats that explicitly have audio, or where it's implied by yt-dlp's combination
                    # For HLS streams (protocol: m3u8_native), yt-dlp typically handles audio muxing.
                    
                    resolution_str = f"{f.get('width')}x{f.get('height')}" if f.get('width') and f.get('height') else f.get('resolution')

                    # If 'acodec' is 'none', it's usually a video-only stream that yt-dlp can mux with an audio stream.
                    # We still want to show these as download options.
                    
                    # Ensure unique resolutions
                    if resolution_str and resolution_str not in seen_resolutions:
                        video_formats_options.append({
                            "url": f['url'], # This URL might be an HLS manifest, yt-dlp will handle it.
                            "resolution": resolution_str,
                            "filesize": f.get('filesize_approx') or f.get('filesize') # Approx size is often better for HLS
                        })
                        seen_resolutions.add(resolution_str)
            
            # Also consider the 'requested_formats' if available, which might contain combined info
            for rf in info.get('requested_formats', []):
                if rf.get('ext') == 'mp4' and rf.get('vcodec') != 'none' and rf.get('height'):
                    resolution_str = f"{rf.get('width')}x{rf.get('height')}" if rf.get('width') and rf.get('height') else rf.get('resolution')
                    if resolution_str and resolution_str not in seen_resolutions:
                        video_formats_options.append({
                            "url": rf['url'], # This URL might be an HLS manifest, yt-dlp will handle it.
                            "resolution": resolution_str,
                            "filesize": rf.get('filesize_approx') or rf.get('filesize')
                        })
                        seen_resolutions.add(resolution_str)

            if not video_formats_options:
                 return jsonify({"error": "No downloadable video formats found for this tweet."}), 404

            # Sort by height for better user experience (highest resolution first)
            # We'll need to parse the height from the resolution string if it's like "480x600"
            def get_height_from_resolution(res_str):
                match = re.search(r'x(\d+)', res_str) # Matches "x600" to get 600
                if match:
                    return int(match.group(1))
                return 0 # Default if height not found

            video_formats_options.sort(key=lambda x: get_height_from_resolution(x['resolution']), reverse=True)
            
            # Remove duplicate resolutions, keeping the first (highest quality after sorting)
            final_video_formats = []
            added_resolutions = set()
            for fmt in video_formats_options:
                if fmt['resolution'] not in added_resolutions:
                    final_video_formats.append(fmt)
                    added_resolutions.add(fmt['resolution'])

            return jsonify({"formats": final_video_formats})

    except yt_dlp.DownloadError as e:
        print(f"YT-DLP Error: {e}")
        return jsonify({"error": f"Error extracting video information: {str(e)}"}), 500
    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

@app.route('/download_video', methods=['POST'])
def download_video():
    video_url = request.json.get('video_url')
    resolution = request.json.get('resolution', 'unknown_resolution') # Get resolution to include in filename
    
    # Use yt-dlp's default naming to get a more sensible filename
    # We will instruct yt-dlp to download directly using the provided URL
    # and to combine video+audio if necessary.
    
    def download_in_thread():
        try:
            # yt-dlp is smart enough to handle HLS manifests (.m3u8) as direct download URLs
            # when you pass them to ydl.download(). It will fetch segments and mux.
            # We don't need a specific filename here, yt-dlp will generate one.
            # Let's ensure the output template includes the resolution for clarity.
            
            # Sanitize resolution for filename (remove 'x' and other special chars)
            sanitized_resolution = re.sub(r'[^\w\d_]', '', resolution).replace('x', '_')
            
            # Output template: %(title)s-%(id)s.%(ext)s or similar
            # For X, title might be empty, so fall back to %(id)s
            output_template = os.path.join(DOWNLOAD_DIR, f"%(id)s_{sanitized_resolution}.%(ext)s")

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'outtmpl': output_template,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Ensure MP4 and muxing
                'merge_output_format': 'mp4', # Explicitly merge to MP4 if streams are separate
                'extractor_args': {'x': {'skip_hls_ts': True}},
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # The video_url passed here might be an HLS manifest or a direct video URL.
                # yt-dlp knows how to handle both.
                ydl.download([video_url])
            print(f"Downloaded video for {video_url} (resolution: {resolution}) to {DOWNLOAD_DIR}")
        except Exception as e:
            print(f"Error downloading {video_url}: {e}")

    # Start download in a separate thread to not block the main Flask thread
    threading.Thread(target=download_in_thread).start()

    # Respond immediately to the client that download has started
    return jsonify({"message": "Download initiated. Check your server's downloads folder shortly."})

if __name__ == '__main__':
    app.run(debug=True)