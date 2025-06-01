document.addEventListener('DOMContentLoaded', () => {
    const tweetUrlInput = document.getElementById('tweetUrl');
    const getVideoBtn = document.getElementById('getVideoBtn');
    const loadingDiv = document.getElementById('loading');
    const errorMessageDiv = document.getElementById('errorMessage');
    const downloadOptionsDiv = document.getElementById('downloadOptions');
    const resolutionListDiv = document.getElementById('resolutionList');

    let currentTweetTitle = ''; // Variable to store the tweet title
    let currentUploader = '';   // Variable to store the uploader

    getVideoBtn.addEventListener('click', async () => {
        const tweetUrl = tweetUrlInput.value.trim();
        if (!tweetUrl) {
            displayMessage('Please enter a Twitter/X URL.', 'error');
            return;
        }

        // Client-side URL validation for Twitter/X tweet links
        // Updated regex to accept both twitter.com and x.com
        const twitterUrlPattern = /https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/\w+\/status\/\d+/;
        if (!twitterUrlPattern.test(tweetUrl)) {
            displayMessage('Invalid Twitter/X URL format. Please use a link like "https://x.com/user/status/123456789" or "https://twitter.com/user/status/123456789".', 'error');
            return;
        }

        showLoading();
        clearMessages();
        hideDownloadOptions();

        try {
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ tweet_url: tweetUrl })
            });

            const data = await response.json();

            if (!response.ok) {
                displayMessage(data.error || 'Failed to get video information.', 'error');
                return;
            }

            if (data.formats && data.formats.length > 0) {
                currentTweetTitle = data.tweet_title || ''; // Store the fetched tweet title
                currentUploader = data.uploader || '';     // Store the fetched uploader
                displayDownloadOptions(data.formats);
            } else {
                displayMessage('No downloadable videos found for this tweet.', 'error');
            }

        } catch (error) {
            console.error('Error fetching video info:', error);
            displayMessage('An error occurred while fetching video information. Please check your network or try again.', 'error');
        } finally {
            hideLoading();
        }
    });

    function showLoading() {
        loadingDiv.classList.remove('hidden');
    }

    function hideLoading() {
        loadingDiv.classList.add('hidden');
    }

    function clearMessages() {
        errorMessageDiv.classList.add('hidden');
        errorMessageDiv.textContent = '';
    }

    function displayMessage(message, type = 'info') {
        errorMessageDiv.textContent = message;
        errorMessageDiv.classList.remove('hidden');
        if (type === 'error') {
            errorMessageDiv.style.backgroundColor = '#f2dede';
            errorMessageDiv.style.borderColor = '#ebccd1';
            errorMessageDiv.style.color = '#d9534f';
        } else { // info message
            errorMessageDiv.style.backgroundColor = '#dff0d8';
            errorMessageDiv.style.borderColor = '#d6e9c6';
            errorMessageDiv.style.color = '#3c763d';
        }
    }

    function hideDownloadOptions() {
        downloadOptionsDiv.classList.add('hidden');
        resolutionListDiv.innerHTML = ''; // Clear previous options
    }

    function displayDownloadOptions(formats) {
        resolutionListDiv.innerHTML = ''; // Clear previous options
        formats.forEach(format => {
            const item = document.createElement('div');
            item.classList.add('resolution-item');

            const info = document.createElement('span');
            // Calculate file size in MB, or 'N/A' if unknown
            const fileSizeMB = format.filesize ? (format.filesize / (1024 * 1024)).toFixed(2) : 'N/A';
            info.classList.add('resolution-info');
            // Correctly display resolution and file size (ensure no extra '$' characters here)
            info.textContent = `${format.resolution} (${fileSizeMB} MB)`;

            const downloadButton = document.createElement('button');
            downloadButton.textContent = 'Download';
            // Pass the currentTweetTitle to the download function
            downloadButton.addEventListener('click', () => initiateStreamDownload(format.url, format.resolution, currentTweetTitle));

            item.appendChild(info);
            item.appendChild(downloadButton);
            resolutionListDiv.appendChild(item);
        });
        downloadOptionsDiv.classList.remove('hidden');
    }

    // Updated function signature to accept filename_base
    async function initiateStreamDownload(videoUrl, resolution, filenameBase) {
        displayMessage(`Preparing to download ${resolution} video... This may take a moment.`, 'info');
        showLoading();

        try {
            const response = await fetch('/stream_download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                // Send the filename_base along with video_url and resolution
                body: JSON.stringify({
                    video_url: videoUrl,
                    resolution: resolution,
                    filename_base: filenameBase // Send the tweet title here
                })
            });

            if (!response.ok) {
                // If the backend returns an error (e.g., 500 status), parse the JSON error
                const errorData = await response.json();
                displayMessage(errorData.error || 'Failed to initiate download.', 'error');
            } else {
                // The fetch request was successful. Now, trigger the browser download.
                // fetch doesn't automatically trigger a download, even with Content-Disposition headers.
                // We need to create a Blob from the response and then create a temporary URL for it.

                const blob = await response.blob(); // Get the response body as a Blob
                const downloadUrl = window.URL.createObjectURL(blob); // Create a temporary URL for the Blob

                const a = document.createElement('a'); // Create a temporary anchor element
                a.href = downloadUrl; // Set its href to the Blob URL

                // Extract filename from Content-Disposition header if available, otherwise use fallback
                let suggestedFileName = `${filenameBase}_${resolution}.mp4`; // Fallback name
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?$/);
                    if (filenameMatch && filenameMatch[1]) {
                        suggestedFileName = filenameMatch[1];
                    }
                }
                a.download = suggestedFileName; // Set the download attribute with the suggested filename

                document.body.appendChild(a); // Append the anchor to the body (necessary for .click() to work in some browsers)
                a.click(); // Programmatically click the anchor to trigger download
                document.body.removeChild(a); // Clean up the temporary anchor
                window.URL.revokeObjectURL(downloadUrl); // Revoke the temporary URL to free up memory

                displayMessage(`Download of ${resolution} video initiated. Check your browser's downloads.`, 'info');
            }

        } catch (error) {
            console.error('Error during streaming download:', error);
            displayMessage('An error occurred during download. Please check your network or try again.', 'error');
        } finally {
            hideLoading();
        }
    }
});