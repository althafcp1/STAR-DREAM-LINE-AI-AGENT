/**
 * DreamLine AI Agent – Frontend Controller v2.0
 * Dream Line Travels | Your Intelligent Travel Companion
 * Features: English/Arabic, Audio, Responsive, Gemini Chat
 */

/* ── STATE ──────────────────────────────────────────────────── */
let currentTripId     = null;
let currentDestination = "Dubai";
let currentDuration   = 3;
let currentLang       = "en";           // "en" | "ar"
let activePlanRequest = 0;
let agentTimers       = [];
let activeAudio       = null;           // currently playing Audio object
let speechSynthAvailable = window.speechSynthesis && window.SpeechSynthesisUtterance;

const currentUserId = (() => {
  const key = "dreamlineConversationUserId";
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = window.crypto && typeof window.crypto.randomUUID === "function"
      ? window.crypto.randomUUID()
      : `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(key, id);
  }
  return id;
})();

/* ── TRANSLATIONS ───────────────────────────────────────────── */
const T = {
  en: {
    welcomeMsg:      "Hello! Welcome to Dream Line Travels. I'm DreamLine AI, your personal travel assistant. Ask me about Dubai, Abu Dhabi, hotels, itineraries, or any travel question! 🌟",
    typingMsg:       "DreamLine AI is thinking...",
    sendBtn:         "Send",
    clearBtn:        "🗑️ Clear",
    langInfo:        "Responding in: English",
    chatHintOpen:    "Open",
    chatHintClose:   "Close",
    errorPrefix:     "Unable to get an AI response",
    retryLabel:      "Retry",
    chatPlaceholder: "Ask about Dubai, hotels, itineraries...",
    noKey:           "⚠️ Gemini AI is not configured. Chat responses will be unavailable until you add your API key to backend/.env.",
    getKeyLink:      "Get a free key here →",
    planningBtn:     "⏳ DreamLine AI is planning your trip...",
    generateBtn:     "🚀 Generate Itinerary with DreamLine AI",
    noTrip:          "Please generate a trip plan first.",
    invalidForm:     "Please enter valid trip details.",
    agentSteps: [
      ["agent-manager",   "Analyzing trip parameters..."],
      ["agent-dest",      "Researching destinations..."],
      ["agent-weather",   "Checking weather..."],
      ["agent-hotel",     "Finding hotels..."],
      ["agent-budget",    "Calculating budget..."],
      ["agent-itinerary", "Preparing itinerary..."]
    ],
    agentDone:    "Task Completed ✓",
    agentWaiting: "Waiting...",
  },
  ar: {
    welcomeMsg:      "مرحباً! أهلاً بك في دريم لاين للسفر. أنا مساعد دريم لاين الذكي للسفر. اسألني عن دبي وأبوظبي والفنادق والبرامج السياحية أو أي سؤال عن السفر! 🌟",
    typingMsg:       "دريم لاين الذكي يفكر...",
    sendBtn:         "إرسال",
    clearBtn:        "🗑️ مسح",
    langInfo:        "يرد بـ: العربية",
    chatHintOpen:    "افتح",
    chatHintClose:   "أغلق",
    errorPrefix:     "تعذّر الحصول على رد الذكاء الاصطناعي",
    retryLabel:      "إعادة المحاولة",
    chatPlaceholder: "اسأل عن دبي، الفنادق، البرامج السياحية...",
    noKey:           "⚠️ لم يتم تهيئة Gemini AI. لن تتوفر ردود المحادثة حتى تُضيف مفتاح API إلى backend/.env.",
    getKeyLink:      "احصل على مفتاح مجاني هنا ←",
    planningBtn:     "⏳ دريم لاين الذكي يخطط رحلتك...",
    generateBtn:     "🚀 إنشاء برنامج سياحي مع دريم لاين",
    noTrip:          "الرجاء إنشاء خطة سفر أولاً.",
    invalidForm:     "يرجى إدخال تفاصيل رحلة صحيحة.",
    agentSteps: [
      ["agent-manager",   "جاري تحليل معلمات الرحلة..."],
      ["agent-dest",      "جاري البحث عن الوجهات..."],
      ["agent-weather",   "جاري التحقق من الطقس..."],
      ["agent-hotel",     "جاري البحث عن الفنادق..."],
      ["agent-budget",    "جاري احتساب الميزانية..."],
      ["agent-itinerary", "جاري إعداد البرنامج السياحي..."]
    ],
    agentDone:    "اكتملت المهمة ✓",
    agentWaiting: "في الانتظار...",
  }
};

function t(key) {
  return (T[currentLang] || T.en)[key] || T.en[key] || key;
}

/* ── DOM HELPERS ────────────────────────────────────────────── */
function el(id) { return document.getElementById(id); }

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = String(text);
  return element;
}

function setText(id, value) {
  const element = el(id);
  if (element) element.textContent = String(value ?? "—");
}

function formatMoney(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return `$${amount.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

async function getApiError(response) {
  let message = `Server returned HTTP ${response.status}`;
  try {
    const data = await response.json();
    if (typeof data.detail === "string") message = data.detail;
  } catch { /* keep status message */ }
  return message;
}

/* ── LANGUAGE SWITCHER ──────────────────────────────────────── */
function applyLanguage(lang) {
  currentLang = lang;
  const html = document.getElementById("htmlRoot");
  html.setAttribute("lang", lang);
  html.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");

  // Update all data-en/data-ar elements
  document.querySelectorAll("[data-en]").forEach(node => {
    const val = node.getAttribute(`data-${lang}`) || node.getAttribute("data-en");
    if (node.tagName === "INPUT" || node.tagName === "TEXTAREA") {
      node.placeholder = val;
    } else {
      // Only update if the element has no children that shouldn't be overwritten
      if (!node.querySelector("input, button, select, a")) {
        node.textContent = val;
      }
    }
  });

  // Update select option text
  document.querySelectorAll("option[data-en]").forEach(opt => {
    const val = opt.getAttribute(`data-${lang}`) || opt.getAttribute("data-en");
    if (val) opt.textContent = val;
  });

  // Update chat input placeholder
  const chatInputEl = el("chatInput");
  if (chatInputEl) chatInputEl.placeholder = t("chatPlaceholder");

  // Update send button
  const sendBtnEl = el("sendChatBtn");
  if (sendBtnEl) {
    const span = sendBtnEl.querySelector("span[data-en]") || sendBtnEl;
    span.textContent = t("sendBtn");
  }

  // Update clear button
  const clearBtnEl = el("clearChatBtn");
  if (clearBtnEl) clearBtnEl.textContent = t("clearBtn");

  // Update lang info
  const langInfoEl = el("chatLangInfo");
  if (langInfoEl) langInfoEl.textContent = t("langInfo");

  // Update generate button
  const generateBtnEl = el("generatePlanBtn");
  if (generateBtnEl && !generateBtnEl.disabled) {
    const span = generateBtnEl.querySelector("span[data-en]") || generateBtnEl;
    span.textContent = t("generateBtn");
  }

  // Update chat hint
  const chatHintEl = document.querySelector(".chat-hint");
  if (chatHintEl) {
    const isOpen = el("chatDrawer") && !el("chatDrawer").classList.contains("collapsed");
    chatHintEl.textContent = isOpen ? t("chatHintClose") : t("chatHintOpen");
  }

  // Update API warning text if visible
  const apiWarningEl = el("apiWarningText");
  if (apiWarningEl) {
    apiWarningEl.innerHTML = `${t("noKey")} <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener">${t("getKeyLink")}</a>`;
  }

  // Update lang buttons
  document.querySelectorAll(".lang-btn").forEach(btn => {
    const isActive = btn.dataset.lang === lang;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-pressed", String(isActive));
  });
}

/* ── API KEY CHECK ──────────────────────────────────────────── */
async function checkApiKeyStatus() {
  try {
    const r = await fetch("/api/check-key");
    if (!r.ok) return;
    const data = await r.json();
    if (!data.gemini_configured) {
      const banner = el("apiWarning");
      if (banner) banner.style.display = "block";
    }
  } catch { /* server might not be running; ignore */ }
}

/* ── CHAT ───────────────────────────────────────────────────── */
const chatMessages = el("chatMessages");

function appendChatBubble(role, message, extraClass = "", withAudio = false) {
  const wrap = document.createElement("div");
  wrap.className = `chat-bubble-wrap ${role}`;

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role} ${extraClass}`.trim();
  bubble.textContent = String(message ?? "");

  if (withAudio && role === "assistant" && !extraClass.includes("error") && !extraClass.includes("typing")) {
    const audioBtn = document.createElement("button");
    audioBtn.className = "audio-btn";
    audioBtn.title = currentLang === "ar" ? "استمع" : "Listen";
    audioBtn.setAttribute("aria-label", currentLang === "ar" ? "تشغيل الصوت" : "Play audio");
    audioBtn.textContent = "🔊";
    audioBtn.addEventListener("click", () => speakMessage(message, audioBtn));
    wrap.appendChild(bubble);
    wrap.appendChild(audioBtn);
  } else {
    wrap.appendChild(bubble);
  }

  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return bubble;
}

function appendTypingIndicator() {
  const indicator = appendChatBubble("assistant", t("typingMsg"), "typing-indicator");
  indicator.setAttribute("aria-label", t("typingMsg"));
  return indicator.parentElement; // return the wrap div
}

function clearChat() {
  while (chatMessages.firstChild) {
    chatMessages.removeChild(chatMessages.firstChild);
  }
  // Re-add welcome message
  appendChatBubble("assistant", t("welcomeMsg"), "", false);
}

/* ── SPEECH SYNTHESIS (Audio) ───────────────────────────────── */
function speakMessage(text, btnEl) {
  if (!speechSynthAvailable) {
    showAudioFallbackMessage();
    return;
  }

  // Stop any currently playing audio
  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    document.querySelectorAll(".audio-btn.playing").forEach(b => b.classList.remove("playing"));
    if (btnEl.classList.contains("playing")) {
      btnEl.classList.remove("playing");
      return; // toggle off
    }
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang   = currentLang === "ar" ? "ar-AE" : "en-US";
  utterance.rate   = 0.95;
  utterance.pitch  = 1.0;

  // Try to pick a matching voice
  const voices = window.speechSynthesis.getVoices();
  const langCode = currentLang === "ar" ? "ar" : "en";
  const matchVoice = voices.find(v => v.lang.startsWith(langCode) && !v.name.includes("Google"));
  const fallbackVoice = voices.find(v => v.lang.startsWith(langCode));
  if (matchVoice) utterance.voice = matchVoice;
  else if (fallbackVoice) utterance.voice = fallbackVoice;

  btnEl.classList.add("playing");
  btnEl.textContent = "⏹";

  utterance.onend = () => {
    btnEl.classList.remove("playing");
    btnEl.textContent = "🔊";
  };
  utterance.onerror = () => {
    btnEl.classList.remove("playing");
    btnEl.textContent = "🔊";
  };

  window.speechSynthesis.speak(utterance);
}

function showAudioFallbackMessage() {
  appendChatBubble(
    "assistant",
    currentLang === "ar"
      ? "متصفحك لا يدعم التحدث الآلي. يرجى استخدام متصفح حديث."
      : "Your browser does not support speech synthesis. Please use a modern browser.",
    "error"
  );
}

/* ── SEND CHAT MESSAGE ──────────────────────────────────────── */
async function sendChatMessage() {
  const chatInputEl   = el("chatInput");
  const sendChatBtnEl = el("sendChatBtn");
  const message       = chatInputEl.value.trim();

  if (!message || sendChatBtnEl.disabled) return;

  appendChatBubble("user", message);
  chatInputEl.value = "";

  sendChatBtnEl.disabled    = true;
  sendChatBtnEl.textContent = "...";
  const typingWrap = appendTypingIndicator();

  try {
    const response = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trip_id:      currentTripId,
        user_id:      currentUserId,
        destination:  currentDestination,
        duration_days: currentDuration,
        language:     currentLang,
        message
      })
    });

    if (!response.ok) {
      throw new Error(await getApiError(response));
    }

    const data = await response.json();
    if (typeof data.reply !== "string" || !data.reply.trim()) {
      throw new Error("The server returned an empty AI response.");
    }

    typingWrap.remove();
    appendChatBubble("assistant", data.reply, "", true);

    if (data.updated_plan) {
      currentTripId        = data.updated_plan.trip_id      || currentTripId;
      currentDestination   = data.updated_plan.destination  || currentDestination;
      currentDuration      = data.updated_plan.duration_days || currentDuration;
      renderDashboard(data.updated_plan);
      el("resultsDashboard").classList.add("active");
    }

  } catch (error) {
    console.error("Chat failed:", error);
    if (typingWrap && typingWrap.parentElement) typingWrap.remove();

    const errMsg = `${t("errorPrefix")}: ${error.message}`;
    const errBubble = appendChatBubble("assistant", errMsg, "error");

    // Add retry button
    const retryBtn = document.createElement("button");
    retryBtn.className = "chat-tool-btn";
    retryBtn.style.cssText = "margin-top:8px; display:block; font-size:12px;";
    retryBtn.textContent = `🔄 ${t("retryLabel")}`;
    retryBtn.onclick = () => {
      retryBtn.closest(".chat-bubble-wrap").remove();
      el("chatInput").value = message;
      sendChatMessage();
    };
    if (errBubble.parentElement) {
      errBubble.parentElement.appendChild(retryBtn);
    }

  } finally {
    if (typingWrap && typingWrap.parentElement) typingWrap.remove();
    sendChatBtnEl.disabled    = false;
    sendChatBtnEl.textContent = t("sendBtn");
    chatInputEl.focus();
  }
}

/* ── AGENT TRACKER ──────────────────────────────────────────── */
function clearAgentTimers() {
  agentTimers.forEach(clearTimeout);
  agentTimers = [];
}

function resetAgentTracker() {
  clearAgentTimers();
  document.querySelectorAll(".agent-card").forEach(card => {
    card.className = "agent-card";
    const statusEl = card.querySelector(".status-text");
    if (statusEl) statusEl.textContent = t("agentWaiting");
  });
}

function simulateAgentFlow() {
  const steps = t("agentSteps");
  steps.forEach(([id, text], index) => {
    const timer = setTimeout(() => {
      const card = el(id);
      if (!card) return;
      card.classList.add("running");
      const statusEl = card.querySelector(".status-text");
      if (statusEl) statusEl.textContent = text;
    }, index * 450);
    agentTimers.push(timer);
  });
}

function completeAllAgents() {
  document.querySelectorAll(".agent-card").forEach(card => {
    card.className = "agent-card done";
    const statusEl = card.querySelector(".status-text");
    if (statusEl) statusEl.textContent = t("agentDone");
  });
}

/* ── DASHBOARD RENDER ───────────────────────────────────────── */
function renderDashboard(data) {
  setText(
    "resDestTitle",
    `${data.destination || currentDestination} (${data.duration_days || currentDuration} Days)`
  );

  setText("resBudgetVal",    formatMoney(data.budget));
  setText("resTravelersVal", `${data.travelers ?? "—"} Guests`);

  // WEATHER
  const weather     = data.weather_summary || {};
  const temperature = weather.temperature_celsius;
  const weatherText = temperature != null
    ? `${temperature}°C, ${weather.condition || "Condition unavailable"}`
    : (weather.condition || "Weather unavailable");
  setText("resWeatherVal",      weatherText);
  setText("resWeatherAdvisory", weather.travel_advisory || "No advisory available.");

  // BUDGET
  const budget = data.budget_breakdown || {};
  setText("resFoodVal",    formatMoney(budget.estimated_food_total_usd));
  setText("resTransitVal", formatMoney(budget.estimated_local_transit_usd));
  setText("resBufferVal",  formatMoney(budget.emergency_buffer_usd));

  // HOTELS
  const hotelsContainer = el("resHotelsList");
  hotelsContainer.replaceChildren();
  const hotels = Array.isArray(data.hotels) ? data.hotels : [];

  if (!hotels.length) {
    hotelsContainer.appendChild(createElement("p", "empty-state", "No hotel recommendations available."));
  }

  hotels.forEach(hotel => {
    const card     = createElement("div", "hotel-item");
    const name     = createElement("h4", "", hotel.name || "Hotel recommendation");
    const details  = createElement("div", "hotel-details", `Area: ${hotel.area || "Not specified"} | ⭐ ${hotel.rating ?? "N/A"}`);
    const price    = createElement("div", "price", `${formatMoney(hotel.nightly_rate_usd)}/night | Total: ${formatMoney(hotel.total_stay_cost_usd)}`);
    const amenities = Array.isArray(hotel.amenities) ? hotel.amenities.join(", ") : "Not specified";
    const amenitiesEl = createElement("div", "hotel-details", `Amenities: ${amenities}`);
    card.append(name, details, price, amenitiesEl);
    hotelsContainer.appendChild(card);
  });

  // ITINERARY
  const timeline = el("resTimeline");
  timeline.replaceChildren();
  const days = Array.isArray(data.daily_itinerary) ? data.daily_itinerary : [];

  if (!days.length) {
    timeline.appendChild(createElement("p", "empty-state", "No itinerary details available."));
  }

  days.forEach(day => {
    const card    = createElement("div", "day-card");
    const heading = createElement("h3", "", `Day ${day.day ?? "—"}: ${day.title || "Exploring"}`);
    card.appendChild(heading);

    const slots = day.slots || {};
    [["Morning", slots.morning], ["Afternoon", slots.afternoon], ["Evening", slots.evening]].forEach(([label, activity]) => {
      const row     = createElement("div", "slot-item");
      const tag     = createElement("span", "slot-tag", label);
      const content = createElement("div", "", activity || "No activity specified");
      row.append(tag, content);
      card.appendChild(row);
    });

    timeline.appendChild(card);
  });
}

/* ── TRIP PLANNING ──────────────────────────────────────────── */
async function handleTripSubmit(event) {
  event.preventDefault();

  const generateBtnEl = el("generatePlanBtn");
  if (generateBtnEl.disabled) return;

  const destination   = el("destination").value.trim();
  const departure     = el("departure").value.trim() || "Abu Dhabi";
  const durationDays  = Number.parseInt(el("duration").value, 10);
  const budget        = Number.parseFloat(el("budget").value);
  const travelers     = Number.parseInt(el("travelers").value, 10);
  const hotelTier     = el("hotelTier").value;
  const preferences   = Array.from(
    document.querySelectorAll('input[name="preferences"]:checked')
  ).map(cb => cb.value);

  if (!destination || !Number.isInteger(durationDays) || durationDays < 1 || durationDays > 14 ||
      !Number.isFinite(budget) || budget < 200 || !Number.isInteger(travelers) || travelers < 1 || travelers > 10) {
    alert(t("invalidForm"));
    return;
  }

  const requestId = ++activePlanRequest;
  currentTripId        = null;
  currentDestination   = destination;
  currentDuration      = durationDays;

  const generateSpan = generateBtnEl.querySelector("span[data-en]") || generateBtnEl;
  generateBtnEl.disabled = true;
  generateSpan.textContent = t("planningBtn");

  el("agentTracker").classList.add("active");
  el("resultsDashboard").classList.remove("active");

  resetAgentTracker();
  simulateAgentFlow();

  try {
    const response = await fetch("/api/trip/plan", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        destination,
        departure_city:        departure,
        duration_days:         durationDays,
        budget,
        travelers_count:       travelers,
        travel_preferences:    preferences.length ? preferences : ["culture", "sightseeing"],
        accommodation_type:    hotelTier,
        user_id:               currentUserId
      })
    });

    if (!response.ok) throw new Error(await getApiError(response));

    const data = await response.json();
    if (!data.trip_id) throw new Error("The server did not return a trip ID.");
    if (requestId !== activePlanRequest) return;

    currentTripId = data.trip_id;
    clearAgentTimers();
    completeAllAgents();
    renderDashboard(data);
    el("resultsDashboard").classList.add("active");
    el("resultsDashboard").scrollIntoView({ behavior: "smooth", block: "start" });

  } catch (error) {
    if (requestId !== activePlanRequest) return;
    console.error("Trip planning failed:", error);
    alert(`${t("errorPrefix")}: ${error.message}`);
    resetAgentTracker();
    el("agentTracker").classList.remove("active");
  } finally {
    if (requestId === activePlanRequest) {
      clearAgentTimers();
      generateBtnEl.disabled = false;
      generateSpan.textContent = t("generateBtn");
    }
  }
}

/* ── BOOT ───────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {

  // Language buttons
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => applyLanguage(btn.dataset.lang));
  });

  // Trip form
  const tripFormEl = el("tripFormEl");
  if (tripFormEl) tripFormEl.addEventListener("submit", handleTripSubmit);

  // PDF download
  const downloadPdfBtnEl = el("downloadPdfBtn");
  if (downloadPdfBtnEl) {
    downloadPdfBtnEl.addEventListener("click", () => {
      if (!currentTripId) { alert(t("noTrip")); return; }
      window.open(`/api/trip/${encodeURIComponent(currentTripId)}/pdf`, "_blank", "noopener,noreferrer");
    });
  }

  // Chat drawer toggle
  const chatHeaderEl  = el("chatHeader");
  const chatDrawerEl  = el("chatDrawer");
  const chatHintEl    = chatHeaderEl ? chatHeaderEl.querySelector(".chat-hint") : null;

  if (chatHeaderEl && chatDrawerEl) {
    chatHeaderEl.addEventListener("click", () => {
      const collapsed = chatDrawerEl.classList.toggle("collapsed");
      chatHeaderEl.setAttribute("aria-expanded", String(!collapsed));
      if (chatHintEl) chatHintEl.textContent = collapsed ? t("chatHintOpen") : t("chatHintClose");
      if (!collapsed) el("chatInput") && el("chatInput").focus();
    });
  }

  // Send chat button
  const sendChatBtnEl = el("sendChatBtn");
  if (sendChatBtnEl) sendChatBtnEl.addEventListener("click", sendChatMessage);

  // Enter to send
  const chatInputEl = el("chatInput");
  if (chatInputEl) {
    chatInputEl.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    });
  }

  // Clear chat
  const clearChatBtnEl = el("clearChatBtn");
  if (clearChatBtnEl) clearChatBtnEl.addEventListener("click", clearChat);

  // Initial welcome message
  appendChatBubble("assistant", t("welcomeMsg"), "", false);

  // Apply default language (English)
  applyLanguage("en");

  // Check if Gemini is configured and show warning if not
  checkApiKeyStatus();

  // Pre-load speech synthesis voices (some browsers load lazily)
  if (window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
  }
});
