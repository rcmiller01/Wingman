
const url = 'http://host.docker.internal:11434/api/embeddings';
const body = JSON.stringify({
    model: 'nomic-embed-text',
    prompt: 'hello world'
});
console.log('Fetching', url);
fetch(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' } })
    .then(r => {
        console.log('Status:', r.status);
        return r.text();
    })
    .then(text => {
        console.log('Response length:', text.length);
        try {
            const json = JSON.parse(text);
            if (json.embedding) {
                console.log('Embedding detected. Length:', json.embedding.length);
            } else {
                console.log('No embedding in response:', text.substring(0, 200));
            }
        } catch (e) {
            console.log('Failed to parse JSON:', text.substring(0, 200));
        }
    })
    .catch(console.error);
