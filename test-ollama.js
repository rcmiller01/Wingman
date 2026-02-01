
const url = 'http://host.docker.internal:11434/api/generate';
const body = JSON.stringify({
    model: 'qwen2.5:7b',
    prompt: 'hi',
    stream: false
});
console.log('Fetching', url);
fetch(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' } })
    .then(r => {
        console.log('Status:', r.status);
        return r.text();
    })
    .then(console.log)
    .catch(console.error);
