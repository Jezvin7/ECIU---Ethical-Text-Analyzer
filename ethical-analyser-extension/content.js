let lastAnalyzedSignature = "";
let latestCandidateSignature = "";
let stableTimer = null;
let isAnalyzing = false;

let latestTypedText = "";
let lastSubmittedUserText = "";
let promptWasSubmitted = false;

let recentGeneratedCandidates = [];

const MIN_TEXT_LENGTH = 80;
const STABILITY_WAIT_MS = 4500;


/* =========================================================
   1. Track when the user submits a prompt
========================================================= */

document.addEventListener("input", (event) => {
  const target = event.target;

  const isTextInput =
    target.tagName === "TEXTAREA" ||
    target.getAttribute("contenteditable") === "true";

  if (isTextInput) {
    latestTypedText = target.innerText || target.value || "";
  }
}, true);


document.addEventListener("keydown", (event) => {
  const target = event.target;

  const isTextInput =
    target.tagName === "TEXTAREA" ||
    target.getAttribute("contenteditable") === "true";

  if (isTextInput && event.key === "Enter" && !event.shiftKey) {
    markPromptSubmitted();
  }
}, true);


document.addEventListener("click", (event) => {
  const button = event.target.closest("button");

  if (!button) {
    return;
  }

  const ariaLabel = button.getAttribute("aria-label")?.toLowerCase() || "";
  const title = button.getAttribute("title")?.toLowerCase() || "";
  const text = button.innerText?.toLowerCase() || "";

  const looksLikeSendButton =
    ariaLabel.includes("send") ||
    ariaLabel.includes("submit") ||
    ariaLabel.includes("send prompt") ||
    title.includes("send") ||
    title.includes("submit") ||
    text.includes("send");

  if (looksLikeSendButton) {
    markPromptSubmitted();
  }
}, true);


function markPromptSubmitted() {
  const typed = cleanText(latestTypedText);

  if (typed) {
    lastSubmittedUserText = typed;
  }

  promptWasSubmitted = true;
  recentGeneratedCandidates = [];
  latestCandidateSignature = "";

  clearTimeout(stableTimer);
}


/* =========================================================
   2. Text cleaning
========================================================= */

function cleanText(text) {
  if (!text) {
    return "";
  }

  return text
    .replace(/\u200B/g, "")
    .replace(/\s+/g, " ")
    .replace(/^Gemini said\s*/i, "")
    .replace(/^Claude said\s*/i, "")
    .replace(/^ChatGPT said\s*/i, "")
    .trim();
}


function isSameAsUserPrompt(text) {
  const cleanedText = cleanText(text);
  const cleanedPrompt = cleanText(lastSubmittedUserText);

  if (!cleanedText || !cleanedPrompt) {
    return false;
  }

  return cleanedText === cleanedPrompt;
}


function isNoiseText(text) {
  const lower = text.toLowerCase();

  const noisePatterns = [
    "gemini is ai and can make mistakes",
    "your privacy and gemini",
    "opens in a new window",
    "terms and privacy",
    "claude can make mistakes",
    "chatgpt can make mistakes",
    "check important info",
    "google apps",
    "new chat",
    "recent",
    "settings and help"
  ];

  return noisePatterns.some(pattern => lower.includes(pattern));
}


function isValidCandidateText(text) {
  const cleaned = cleanText(text);

  if (!cleaned) {
    return false;
  }

  if (cleaned.length < MIN_TEXT_LENGTH) {
    return false;
  }

  if (cleaned.length > 12000) {
    return false;
  }

  if (isSameAsUserPrompt(cleaned)) {
    return false;
  }

  if (isNoiseText(cleaned)) {
    return false;
  }

  return true;
}


/* =========================================================
   3. Extract real URLs hidden behind clickable source labels
========================================================= */

function normalizeExternalSourceUrl(rawHref) {
  if (!rawHref) {
    return null;
  }

  try {
    const url = new URL(rawHref, window.location.href);

    if (!["http:", "https:"].includes(url.protocol)) {
      return null;
    }

    const currentHost = window.location.hostname;
    const host = url.hostname.toLowerCase();

    // Ignore links back to the LLM itself
    const internalHosts = [
      "chatgpt.com",
      "chat.openai.com",
      "gemini.google.com",
      "claude.ai"
    ];

    if (
      host === currentHost ||
      internalHosts.some(internal => host.includes(internal))
    ) {
      return null;
    }

    // Decode Google redirect links when possible
    if (
      host === "www.google.com" ||
      host === "google.com"
    ) {
      const redirected =
        url.searchParams.get("url") ||
        url.searchParams.get("q");

      if (redirected) {
        return normalizeExternalSourceUrl(redirected);
      }
    }

    // Ignore obvious non-source utility links
    const lowerHref = url.href.toLowerCase();

    const unwantedPatterns = [
      "privacy",
      "terms",
      "support.google",
      "policies.google",
      "accounts.google"
    ];

    if (unwantedPatterns.some(pattern => lowerHref.includes(pattern))) {
      return null;
    }

    return url.href;

  } catch (error) {
    return null;
  }
}


function extractSourceLinksFromElement(element) {
  if (!element) {
    return [];
  }

  const anchors = Array.from(element.querySelectorAll("a[href]"));

  const links = anchors
    .map(anchor => normalizeExternalSourceUrl(anchor.href))
    .filter(Boolean);

  return [...new Set(links)];
}


/* =========================================================
   4. Build a clean response bundle: text + hidden URLs
========================================================= */

function buildResponseBundle(element) {
  if (!element) {
    return null;
  }

  const text = cleanText(element.innerText);
  const sourceLinks = extractSourceLinksFromElement(element);

  if (!isValidCandidateText(text)) {
    return null;
  }

  return {
    text,
    source_links: sourceLinks
  };
}


function bundleSignature(bundle) {
  if (!bundle) {
    return "";
  }

  return `${bundle.text}|||${bundle.source_links.join("|||")}`;
}


/* =========================================================
   5. ChatGPT extraction
========================================================= */

function extractLatestChatGPTAnswer() {
  const assistantMessages = document.querySelectorAll(
    '[data-message-author-role="assistant"]'
  );

  if (!assistantMessages.length) {
    return null;
  }

  const latest = assistantMessages[assistantMessages.length - 1];
  return buildResponseBundle(latest);
}


/* =========================================================
   6. Gemini extraction
========================================================= */

function extractLatestGeminiAnswer() {
  const selectors = [
    "model-response",
    "message-content",
    ".model-response-text",
    ".response-container",
    "response-container",
    '[class*="model-response"]',
    '[class*="response-content"]'
  ];

  const bundles = [];

  selectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(element => {
      const bundle = buildResponseBundle(element);

      if (bundle) {
        bundles.push(bundle);
      }
    });
  });

  if (!bundles.length) {
    return getBestRecentGeneratedCandidate();
  }

  // Prefer the latest valid candidate in DOM order
  return bundles[bundles.length - 1];
}


/* =========================================================
   7. Claude extraction
========================================================= */

function extractLatestClaudeAnswer() {
  const selectors = [
    '[data-testid="assistant-message"]',
    '[data-testid*="assistant"]',
    ".font-claude-message",
    '[class*="assistant"]',
    "article"
  ];

  const bundles = [];

  selectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(element => {
      const bundle = buildResponseBundle(element);

      if (bundle) {
        bundles.push(bundle);
      }
    });
  });

  if (!bundles.length) {
    return getBestRecentGeneratedCandidate();
  }

  return bundles[bundles.length - 1];
}


/* =========================================================
   8. DOM fallback for Gemini / Claude
========================================================= */

function collectCandidateFromNode(node) {
  if (!promptWasSubmitted) {
    return;
  }

  if (!(node instanceof HTMLElement)) {
    return;
  }

  const bundle = buildResponseBundle(node);

  if (!bundle) {
    return;
  }

  recentGeneratedCandidates.push(bundle);

  if (recentGeneratedCandidates.length > 80) {
    recentGeneratedCandidates.shift();
  }
}


function getBestRecentGeneratedCandidate() {
  const valid = recentGeneratedCandidates.filter(bundle =>
    bundle && isValidCandidateText(bundle.text)
  );

  if (!valid.length) {
    return null;
  }

  valid.sort((a, b) => b.text.length - a.text.length);

  return valid[0];
}


/* =========================================================
   9. Platform router
========================================================= */

function extractLatestLLMAnswer() {
  const hostname = window.location.hostname;

  if (
    hostname.includes("chatgpt.com") ||
    hostname.includes("chat.openai.com")
  ) {
    return extractLatestChatGPTAnswer();
  }

  if (hostname.includes("gemini.google.com")) {
    return extractLatestGeminiAnswer();
  }

  if (hostname.includes("claude.ai")) {
    return extractLatestClaudeAnswer();
  }

  return null;
}


/* =========================================================
   10. Floating popup helpers
========================================================= */

function removeOldPopup() {
  const oldPopup = document.getElementById("ethical-analyser-popup");

  if (oldPopup) {
    oldPopup.remove();
  }
}


function getReliabilityInfo(score) {
  if (score >= 75) {
    return {
      label: "High reliability",
      bg: "#dcfce7",
      color: "#166534"
    };
  }

  if (score >= 50) {
    return {
      label: "Medium reliability",
      bg: "#fef3c7",
      color: "#92400e"
    };
  }

  return {
    label: "Low reliability",
    bg: "#fee2e2",
    color: "#991b1b"
  };
}


function injectSpinnerStyle() {
  if (document.getElementById("ethical-spinner-style")) {
    return;
  }

  const style = document.createElement("style");
  style.id = "ethical-spinner-style";

  style.textContent = `
    .ethical-spinner {
      width: 22px;
      height: 22px;
      border: 3px solid #d1d5db;
      border-top: 3px solid #4f46e5;
      border-radius: 50%;
      animation: ethicalSpin 0.8s linear infinite;
    }

    @keyframes ethicalSpin {
      0% {
        transform: rotate(0deg);
      }

      100% {
        transform: rotate(360deg);
      }
    }
  `;

  document.head.appendChild(style);
}


function createLoadingPopup() {
  removeOldPopup();
  injectSpinnerStyle();

  const popup = document.createElement("div");
  popup.id = "ethical-analyser-popup";

  popup.style.position = "fixed";
  popup.style.bottom = "25px";
  popup.style.right = "25px";
  popup.style.width = "320px";
  popup.style.padding = "16px";
  popup.style.background = "white";
  popup.style.border = "1px solid #ddd";
  popup.style.borderRadius = "12px";
  popup.style.boxShadow = "0 4px 16px rgba(0,0,0,0.18)";
  popup.style.zIndex = "999999";
  popup.style.fontFamily = "Arial, sans-serif";
  popup.style.color = "#111";

  popup.innerHTML = `
    <div style="font-size:16px; font-weight:bold; margin-bottom:14px;">
      Ethical Analyser
    </div>

    <div style="display:flex; align-items:center; gap:10px;">
      <div class="ethical-spinner"></div>
      <div style="font-size:14px;">
        Analyzing generated answer...
      </div>
    </div>
  `;

  document.body.appendChild(popup);
}


function createScorePopup(data) {
  removeOldPopup();

  const popup = document.createElement("div");
  popup.id = "ethical-analyser-popup";

  popup.style.position = "fixed";
  popup.style.bottom = "25px";
  popup.style.right = "25px";
  popup.style.width = "320px";
  popup.style.padding = "16px";
  popup.style.background = "white";
  popup.style.border = "1px solid #ddd";
  popup.style.borderRadius = "12px";
  popup.style.boxShadow = "0 4px 16px rgba(0,0,0,0.18)";
  popup.style.zIndex = "999999";
  popup.style.fontFamily = "Arial, sans-serif";
  popup.style.color = "#111";

  const reliability = getReliabilityInfo(data.trust_score);

  popup.innerHTML = `
    <div style="
      display:flex;
      justify-content:space-between;
      align-items:center;
      margin-bottom:10px;
    ">
      <div style="font-size:16px; font-weight:bold;">
        Ethical Analyser
      </div>

      <button id="ethical-close-btn"
        style="
          border:none;
          background:#f3f4f6;
          border-radius:50%;
          width:28px;
          height:28px;
          cursor:pointer;
          font-size:18px;
        ">
        ×
      </button>
    </div>

    <div style="font-size:13px; color:#6b7280;">
      Overall Trust Score
    </div>

    <div style="font-size:30px; font-weight:bold; margin:4px 0 8px 0;">
      ${data.trust_score}/100
    </div>

    <div style="
      display:inline-block;
      padding:6px 10px;
      border-radius:999px;
      font-size:13px;
      font-weight:bold;
      margin-bottom:12px;
      background:${reliability.bg};
      color:${reliability.color};
    ">
      ${reliability.label}
    </div>

    <div style="
      font-size:13px;
      color:#4b5563;
      line-height:1.45;
      margin-bottom:12px;
    ">
      This score was generated automatically from the latest AI response.
    </div>

    <button id="ethical-details-btn"
      style="
        width:100%;
        padding:10px;
        border:none;
        border-radius:8px;
        cursor:pointer;
        font-weight:bold;
        background:#111827;
        color:white;
      ">
      View Details
    </button>
  `;

  document.body.appendChild(popup);

  document.getElementById("ethical-details-btn").addEventListener("click", () => {
    const detailsUrl =
      `http://localhost:8501/?analysis_id=${data.analysis_id}`;

    window.open(detailsUrl, "_blank");

    popup.remove();
  });

  document.getElementById("ethical-close-btn").addEventListener("click", () => {
    popup.remove();
  });
}


function createErrorPopup() {
  removeOldPopup();

  const popup = document.createElement("div");
  popup.id = "ethical-analyser-popup";

  popup.style.position = "fixed";
  popup.style.bottom = "25px";
  popup.style.right = "25px";
  popup.style.width = "320px";
  popup.style.padding = "16px";
  popup.style.background = "white";
  popup.style.border = "1px solid #ddd";
  popup.style.borderRadius = "12px";
  popup.style.boxShadow = "0 4px 16px rgba(0,0,0,0.18)";
  popup.style.zIndex = "999999";
  popup.style.fontFamily = "Arial, sans-serif";
  popup.style.color = "#111";

  popup.innerHTML = `
    <div style="
      display:flex;
      justify-content:space-between;
      align-items:center;
      margin-bottom:10px;
    ">
      <div style="font-size:16px; font-weight:bold;">
        Ethical Analyser
      </div>

      <button id="ethical-close-btn"
        style="
          border:none;
          background:#f3f4f6;
          border-radius:50%;
          width:28px;
          height:28px;
          cursor:pointer;
          font-size:18px;
        ">
        ×
      </button>
    </div>

    <div style="
      background:#fee2e2;
      color:#991b1b;
      padding:10px;
      border-radius:8px;
      font-size:13px;
      line-height:1.4;
    ">
      Could not analyze the generated answer.
      Make sure <b>browser_api.py</b> is running.
    </div>
  `;

  document.body.appendChild(popup);

  document.getElementById("ethical-close-btn").addEventListener("click", () => {
    popup.remove();
  });
}


/* =========================================================
   11. Send bundle to backend
========================================================= */

function analyzeDetectedBundle(bundle) {
  if (!promptWasSubmitted) {
    return;
  }

  if (!bundle || !isValidCandidateText(bundle.text)) {
    return;
  }

  const signature = bundleSignature(bundle);

  if (signature === lastAnalyzedSignature) {
    return;
  }

  if (isAnalyzing) {
    return;
  }

  lastAnalyzedSignature = signature;
  isAnalyzing = true;

  createLoadingPopup();

  try {
    chrome.runtime.sendMessage(
      {
        type: "ANALYZE_TEXT",
        text: bundle.text,
        source_links: bundle.source_links
      },
      response => {
        isAnalyzing = false;

        if (chrome.runtime.lastError) {
          console.warn(
            "Ethical Analyser message error:",
            chrome.runtime.lastError.message
          );
          return;
        }

        if (!response || !response.success) {
          console.error("Ethical Analyser backend error.");
          createErrorPopup();
          return;
        }

        createScorePopup(response.data);
        promptWasSubmitted = false;
      }
    );
  } catch (error) {
    isAnalyzing = false;

    console.warn(
      "Extension context invalidated. Refresh this LLM page after reloading the extension.",
      error
    );
  }
}


/* =========================================================
   12. Wait until output stabilizes
========================================================= */

function scheduleStableAnswerCheck() {
  if (!promptWasSubmitted) {
    return;
  }

  const currentBundle = extractLatestLLMAnswer();

  if (!currentBundle) {
    return;
  }

  const currentSignature = bundleSignature(currentBundle);

  if (currentSignature !== latestCandidateSignature) {
    latestCandidateSignature = currentSignature;

    clearTimeout(stableTimer);

    stableTimer = setTimeout(() => {
      const finalBundle = extractLatestLLMAnswer();

      if (!finalBundle) {
        return;
      }

      const finalSignature = bundleSignature(finalBundle);

      if (
        promptWasSubmitted &&
        finalSignature === latestCandidateSignature
      ) {
        analyzeDetectedBundle(finalBundle);
      }
    }, STABILITY_WAIT_MS);
  }
}


/* =========================================================
   13. Observe page mutations
========================================================= */

const observer = new MutationObserver((mutations) => {
  if (!promptWasSubmitted) {
    return;
  }

  mutations.forEach(mutation => {
    mutation.addedNodes.forEach(node => {
      collectCandidateFromNode(node);
    });

    if (mutation.target instanceof HTMLElement) {
      collectCandidateFromNode(mutation.target);
    }
  });

  scheduleStableAnswerCheck();
});


observer.observe(document.body, {
  childList: true,
  subtree: true,
  characterData: true
});