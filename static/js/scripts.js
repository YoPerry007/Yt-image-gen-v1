document.getElementById('generateBtn').addEventListener('click', async () => {
    const text = document.getElementById('textInput').value.trim();
    const generateBtn = document.getElementById('generateBtn');
    const gallery = document.getElementById('gallery');
    const loader = document.getElementById('loader');

    if (!text) {
        alert('Please enter some text first.');
        return;
    }

    // Reset UI
    gallery.innerHTML = '';
    gallery.classList.remove('visible');
    loader.style.display = 'flex';
    generateBtn.disabled = true;

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (data.images && data.images.length > 0) {
            data.images.forEach(img => {
                const card = document.createElement('div');
                card.className = 'image-card';
                card.innerHTML = `
                    <div class="image-container">
                        <img src="${img.url}" alt="AI Generated Image" loading="lazy">
                    </div>
                    <div class="image-info">
                        <p>${img.prompt}</p>
                    </div>
                `;
                gallery.appendChild(card);
            });

            loader.style.display = 'none';
            gallery.classList.add('visible');
        } else {
            throw new Error('No images were generated.');
        }

    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate images: ' + error.message);
        loader.style.display = 'none';
    } finally {
        generateBtn.disabled = false;
    }
});
