from flask import Flask, request, jsonify, send_file, Response
import yt_dlp
import re
import os
import threading
import json
import unicodedata # Import unicodedata for better filename sanitization

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

    if not re.match(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+", tweet_url):
        return jsonify({"error": "Invalid Twitter/X URL. Please provide a direct link to a tweet (e.g., https://x.com/user/status/123...)."}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'force_generic_extractor': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'extractor_args': {'twitter': {'skip_hls_ts': True}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tweet_url, download=False)
            
            if 'formats' not in info:
                return jsonify({"error": "No video found in this tweet or no downloadable formats recognized."}), 404

            video_formats_options = []
            seen_resolutions = set()

            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('height'):
                    resolution_str = f"{f.get('width')}x{f.get('height')}" if f.get('width') and f.get('height') else f.get('resolution')

                    if resolution_str and resolution_str not in seen_resolutions:
                        video_formats_options.append({
                            "url": f['url'],
                            "resolution": resolution_str,
                            "filesize": f.get('filesize_approx') or f.get('filesize')
                        })
                        seen_resolutions.add(resolution_str)
            
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

            def get_height_from_resolution(res_str):
                match = re.search(r'x(\d+)', res_str)
                if match:
                    return int(match.group(1))
                return 0

            video_formats_options.sort(key=lambda x: get_height_from_resolution(x['resolution']), reverse=True)
            
            final_video_formats = []
            added_resolutions_post_sort = set()
            for fmt in video_formats_options:
                if fmt['resolution'] not in added_resolutions_post_sort:
                    final_video_formats.append(fmt)
                    added_resolutions_post_sort.add(fmt['resolution'])

            # Extract tweet title/description if available
            tweet_title = info.get('description', '')
            # Get the uploader's screen name as an alternative
            uploader = info.get('uploader', '')

            return jsonify({
                "formats": final_video_formats,
                "tweet_title": tweet_title, # Pass the tweet title to the frontend
                "uploader": uploader # Pass the uploader to the frontend
            })

    except yt_dlp.DownloadError as e:
        print(f"YT-DLP Error during info extraction: {e}")
        return jsonify({"error": f"Error extracting video information: {str(e)}. This might be a private tweet, geo-restricted, or an issue with the video."}), 500
    except Exception as e:
        print(f"General Error during info extraction: {e}")
        return jsonify({"error": "An unexpected error occurred while processing the tweet: " + str(e)}), 500

# Helper function to sanitize filenames
def sanitize_filename(text, max_length=100):
    # Remove emojis and other non-printable characters
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
    # Replace invalid characters with underscores
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    # Replace multiple spaces/underscores with a single underscore
    text = re.sub(r'\s+', '_', text).strip('_')
    text = re.sub(r'_+', '_', text)
    # Trim to max_length to avoid filesystem limits
    if len(text) > max_length:
        text = text[:max_length].rsplit('_', 1)[0] # Try to cut at a word boundary
        if not text: # If text was too short or just symbols
            text = text[:max_length]

    return text.strip()


@app.route('/stream_download', methods=['POST'])
def stream_download():
    video_url = request.json.get('video_url')
    resolution = request.json.get('resolution', 'unknown_resolution')
    # Receive the tweet_filename_base from the frontend
    tweet_filename_base = request.json.get('filename_base', 'twitter_video')

    # The tweet_id_match and tweet_id are still useful for fallback and unique temp names
    tweet_id_match = re.search(r'/status/(\d+)', video_url)
    tweet_id = tweet_id_match.group(1) if tweet_id_match else 'twitter_video'

    if not video_url:
        return jsonify({"error": "Video URL missing."}), 400

    # Ensure the filename is safe for the filesystem
    sanitized_filename_base = sanitize_filename(tweet_filename_base, max_length=150) # Allow a bit more length
    sanitized_resolution = re.sub(r'[^\w\d_]', '', resolution).replace('x', '_')
    
    # Construct the final filename for the user download
    # Prioritize sanitized_filename_base, fallback to tweet_id if base is empty after sanitization
    final_filename = f"{sanitized_filename_base or tweet_id}_{sanitized_resolution}.mp4"

    # Generate a unique filename for the temporary download to avoid conflicts
    temp_filename = f"dl_temp_{os.urandom(8).hex()}_{tweet_id}_{sanitized_resolution}.mp4"
    temp_filepath = os.path.join(DOWNLOAD_DIR, temp_filename)

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': temp_filepath,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'extractor_args': {'twitter': {'skip_hls_ts': True}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        return send_file(temp_filepath, as_attachment=True, download_name=final_filename)

    except yt_dlp.DownloadError as e:
        print(f"YT-DLP Error during download: {e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({"error": f"Failed to download video: {str(e)}. Video might be private or an issue with the link."}), 500
    except Exception as e:
        print(f"General Error during download: {e}")
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return jsonify({"error": "An unexpected error occurred during download: " + str(e)}), 500


if __name__ == '__main__':
    print(f"Cleaning up old temporary files in {DOWNLOAD_DIR}...")
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith('dl_temp_'):
            try:
                os.remove(os.path.join(DOWNLOAD_DIR, f))
                print(f"Removed old temp file: {f}")
            except OSError as e:
                print(f"Error removing old temp file {f}: {e}")
    app.run(debug=True, host='0.0.0.0')