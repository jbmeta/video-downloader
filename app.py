from flask import Flask, request, jsonify, send_file, Response, after_this_request
import yt_dlp
import re
import os
import unicodedata
from datetime import datetime, timedelta
from flaskwebgui import FlaskUI


app = Flask(__name__)

# Define DOWNLOAD_DIR as an absolute path
# This ensures it's always relative to the script's location, not the CWD
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

# Create the downloads directory if it doesn't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Define a cleanup threshold (e.g., 1 hour for temporary files)
CLEANUP_THRESHOLD_HOURS = 1

def cleanup_old_files():
    """
    Cleans up old files in the DOWNLOAD_DIR that are older than CLEANUP_THRESHOLD_HOURS.
    This function runs once on app startup.
    """
    print(f"Starting cleanup of old files in {DOWNLOAD_DIR} (older than {CLEANUP_THRESHOLD_HOURS} hours)...")
    now = datetime.now()
    for f in os.listdir(DOWNLOAD_DIR):
        full_file_path = os.path.join(DOWNLOAD_DIR, f)
        # Ensure it's a file and not a directory, and has a recognizable extension
        if os.path.isfile(full_file_path) and f.endswith(('.mp4', '.m4a', '.webm')): 
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(full_file_path))
                if now - mod_time > timedelta(hours=CLEANUP_THRESHOLD_HOURS):
                    os.remove(full_file_path)
                    print(f"Removed old temp file: {f}")
            except OSError as e:
                print(f"Error removing old temp file {full_file_path}: {e}")
            except Exception as e:
                print(f"Unexpected error during cleanup of {full_file_path}: {e}")
    print("Cleanup finished.")

# Run cleanup on startup
cleanup_old_files()


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

            # Extract tweet title/description if available
            tweet_title = info.get('description', '')
            
            # IMPROVED FALLBACK LOGIC FOR FILENAME
            if not tweet_title:
                tweet_title = info.get('title', '')
            if not tweet_title:
                # Extract tweet ID from the original tweet_url
                tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
                tweet_id_for_fallback = tweet_id_match.group(1) if tweet_id_match else 'unknown_tweet'
                tweet_title = f"{info.get('uploader', 'X_User')}_{tweet_id_for_fallback}"

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
def sanitize_filename(text, max_length=150):
    # Remove emojis and other non-printable characters
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
    # Replace invalid characters with underscores
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    # Replace multiple spaces/underscores with a single underscore
    text = re.sub(r'\s+', '_', text).strip('_')
    text = re.sub(r'_+', '_', text)
    # Ensure it's not empty after initial sanitization
    if not text:
        return ""

    # Trim to max_length to avoid filesystem limits
    if len(text) > max_length:
        # Try to cut at a word boundary (last underscore or space)
        truncated_text = text[:max_length]
        last_boundary = max(truncated_text.rfind('_'), truncated_text.rfind(' '))
        if last_boundary != -1 and last_boundary > max_length // 2: # Ensure it's a meaningful cut, not too early
            text = truncated_text[:last_boundary]
        else:
            text = truncated_text # Fallback if no good boundary or too early cut

    return text.strip()


@app.route('/stream_download', methods=['POST'])
def stream_download():
    """
    Initiates the video download using yt-dlp on the server,
    and then streams the downloaded file back to the client.
    The temporary file is cleaned up after being sent.
    """
    video_url = request.json.get('video_url')
    resolution = request.json.get('resolution', 'unknown_resolution')
    tweet_filename_base = request.json.get('filename_base', 'twitter_video')

    # The tweet_id is still useful for fallback and unique temp names
    tweet_id_match = re.search(r'/status/(\d+)', video_url)
    tweet_id = tweet_id_match.group(1) if tweet_id_match else 'twitter_video'

    if not video_url:
        return jsonify({"error": "Video URL missing."}), 400

    # Ensure the filename is safe for the filesystem
    sanitized_filename_base = sanitize_filename(tweet_filename_base)
    sanitized_resolution = re.sub(r'[^\w\d_]', '', resolution).replace('x', '_')
    
    # Construct the final filename for the user download
    final_download_filename = f"{sanitized_filename_base or tweet_id}_{sanitized_resolution}.mp4"

    # Use a unique component to prevent collisions if multiple downloads happen
    # very rapidly for the same tweet/resolution, but the base should be meaningful.
    unique_id_component = os.urandom(4).hex() 
    
    # Use the meaningful filename as the base for the temporary file as well
    # This means the file saved to disk will also have a relevant name
    temp_filename_on_disk = f"{sanitized_filename_base or tweet_id}_{sanitized_resolution}_{unique_id_component}.mp4"
    temp_filepath = os.path.join(DOWNLOAD_DIR, temp_filename_on_disk)

    # --- DEBUGGING PRINT ---
    print(f"Backend received filename_base (from frontend): '{tweet_filename_base}'")
    print(f"Sanitized filename base: '{sanitized_filename_base}'")
    print(f"Final proposed download filename (for browser): '{final_download_filename}'")
    print(f"Attempting to download to (on disk): '{temp_filepath}'")
    # --- END DEBUGGING PRINT ---

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            # Explicitly set the output template to the full temporary file path
            'outtmpl': temp_filepath, # This is the key: yt-dlp saves *to this path*
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'extractor_args': {'twitter': {'skip_hls_ts': True}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Flask's send_file uses 'download_name' to tell the browser what to name the file.
        # The file sent is still temp_filepath, but the browser renames it.
        response = send_file(temp_filepath, as_attachment=True, download_name=final_download_filename)

        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                    print(f"Cleaned up temp file after sending: {temp_filepath}")
            except Exception as e:
                print(f"Error cleaning up {temp_filepath} after sending: {e}")
            return response

        return response

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
    cleanup_old_files() # Call the dedicated cleanup function

    # Initialize FlaskUI with your desired settings
    gui = FlaskUI(
        app=app,
        server='flask',
        width=800,
        height=700,
        fullscreen=False,
        browser_path=None, # Let FlaskUI discover the browser (recommended)
        # If you want to use a specific browser (e.g., if you have it installed in a custom path):
        # browser_path="C:/Program Files/Google/Chrome/Application/chrome.exe",

    )

    # gui.run() will start the Flask server in a separate thread and then open the GUI window.
    gui.run()
    # app.run(debug=True, host='0.0.0.0')