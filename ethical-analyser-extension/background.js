chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE_TEXT") {
    fetch("http://127.0.0.1:5000/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text: message.text
      })
    })
      .then(response => {
        if (!response.ok) {
          throw new Error("Backend returned an error.");
        }
        return response.json();
      })
      .then(data => {
        sendResponse({
          success: true,
          data: data
        });
      })
      .catch(error => {
        sendResponse({
          success: false,
          error: "Could not connect to Ethical Analyser backend."
        });
      });

    return true;
  }
});