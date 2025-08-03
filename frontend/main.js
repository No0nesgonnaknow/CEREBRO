async function askCerebro() {
  const query = document.getElementById('query').value.trim();
  const status = document.getElementById('status');
  const responseBox = document.getElementById('response');
  const output = document.getElementById('output');
  const mode = document.getElementById('mode');
  const domain = document.getElementById('domain');
  const sources = document.getElementById('sources');
  const duration = document.getElementById('duration');

  if (!query) {
    status.innerText = "Please enter a query.";
    return;
  }

  status.innerText = "Thinking...";
  responseBox.classList.add("hidden");

  try {
    const res = await fetch("http://localhost:5000/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ query })
    });

    const data = await res.json();

    if (data.error) {
      status.innerText = `⚠️ Error: ${data.error}`;
      return;
    }

    output.innerText = data.response;
    mode.innerText = data.mode.toUpperCase();
    domain.innerText = data.domain_used;
    sources.innerText = data.sources_used.join(", ");
    duration.innerText = data.duration_secs;

    responseBox.classList.remove("hidden");
    status.innerText = "";
  } catch (err) {
    status.innerText = "⚠️ Failed to connect to Cerebro backend.";
    console.error(err);
  }
}
