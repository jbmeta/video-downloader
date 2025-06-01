document.addEventListener('DOMContentLoaded', () => {
    const tweetUrlInput = document.getElementById('tweetUrl');
    const getVideoBtn = document.getElementById('getVideoBtn');
    const loadingDiv = document.getElementById('loading');
    const loadingMessageSpan = document.getElementById('loadingMessage'); // NEW ELEMENT REFERENCE
    const errorMessageDiv = document.getElementById('errorMessage');
    const downloadOptionsDiv = document.getElementById('downloadOptions');
    const resolutionListDiv = document.getElementById('resolutionList');

    let currentTweetTitle = '';
    let currentUploader = '';

    getVideoBtn.addEventListener('click', async () => {
        const tweetUrl = tweetUrlInput.value.trim();
        if (!tweetUrl) {
            displayMessage('Please enter a Twitter/X URL.', 'error');
            return;
        }

        const twitterUrlPattern = /https?:\/\/(?:www\.)?(?:twitter\.com|x\.com)\/\w+\/status\/\d+/;
        if (!twitterUrlPattern.test(tweetUrl)) {
            displayMessage('Invalid Twitter/X URL format. Please use a link like "https://x.com/user/status/123456789" or "https://twitter.com/user/status/123456789".', 'error');
            return;
        }

        showLoading('Fetching video information...'); // Pass initial message
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
                currentTweetTitle = data.tweet_title || '';
                currentUploader = data.uploader || '';
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

    // Modified to accept a message
    function showLoading(message = 'Loading...') {
        loadingMessageSpan.textContent = message; // Set the specific loading message
        loadingDiv.classList.remove('hidden');
    }

    function hideLoading() {
        loadingDiv.classList.add('hidden');
        loadingMessageSpan.textContent = ''; // Clear message when hidden
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
        resolutionListDiv.innerHTML = '';
    }

    function displayDownloadOptions(formats) {
        resolutionListDiv.innerHTML = '';
        formats.forEach(format => {
            const item = document.createElement('div');
            item.classList.add('resolution-item');

            const info = document.createElement('span');
            const fileSizeMB = format.filesize ? (format.filesize / (1024 * 1024)).toFixed(2) : 'N/A';
            info.classList.add('resolution-info');
            info.textContent = `${format.resolution} (${fileSizeMB} MB)`;

            const downloadButton = document.createElement('button');
            downloadButton.textContent = 'Download';
            downloadButton.addEventListener('click', () => initiateStreamDownload(format.url, format.resolution, currentTweetTitle));

            item.appendChild(info);
            item.appendChild(downloadButton);
            resolutionListDiv.appendChild(item);
        });
        downloadOptionsDiv.classList.remove('hidden');
    }

    async function initiateStreamDownload(videoUrl, resolution, filenameBase) {
        showLoading(`Downloading ${resolution} video (this may take a moment)...`); // Update loading message
        clearMessages(); // Clear existing messages
        
        try {
            const response = await fetch('/stream_download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    video_url: videoUrl,
                    resolution: resolution,
                    filename_base: filenameBase
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                displayMessage(errorData.error || 'Failed to initiate download.', 'error');
            } else {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                let suggestedFileName = `${filenameBase}_${resolution}.mp4`;
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?$/);
                    if (filenameMatch && filenameMatch[1]) {
                        suggestedFileName = filenameMatch[1];
                    }
                }
                a.download = suggestedFileName;

                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

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