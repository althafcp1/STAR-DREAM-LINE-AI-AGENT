
/**
 * Dream Line Travels
 * DreamLine AI Agent Frontend Controller
 */

let currentTripId = null;
let currentDestination = "Tokyo";
let currentDuration = 3;
const currentUserId = (() => {
  const storageKey = "dreamlineConversationUserId";
  let userId = sessionStorage.getItem(storageKey);

  if (!userId) {
    userId = window.crypto && typeof window.crypto.randomUUID === "function"
      ? window.crypto.randomUUID()
      : `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(storageKey, userId);
  }

  return userId;
})();
let activePlanRequest = 0;
let agentTimers = [];

document.addEventListener("DOMContentLoaded", () => {
  const tripForm = document.getElementById("tripForm");
  const generateBtn = document.getElementById("generatePlanBtn");
  const agentTracker = document.getElementById("agentTracker");
  const resultsDashboard = document.getElementById("resultsDashboard");
  const downloadPdfBtn = document.getElementById("downloadPdfBtn");

  const chatDrawer = document.getElementById("chatDrawer");
  const chatHeader = document.getElementById("chatHeader");
  const chatInput = document.getElementById("chatInput");
  const sendChatBtn = document.getElementById("sendChatBtn");
  const chatMessages = document.getElementById("chatMessages");
  const chatHint = chatHeader.querySelector(".chat-hint");

  // CHAT DRAWER
  chatHeader.addEventListener("click", () => {
    const collapsed = chatDrawer.classList.toggle("collapsed");

    chatHeader.setAttribute("aria-expanded", String(!collapsed));

    if (chatHint) {
      chatHint.textContent = collapsed ? "Open" : "Close";
    }

    if (!collapsed) {
      chatInput.focus();
    }
  });

  // TRIP PLANNING
  tripForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (generateBtn.disabled) return;

    const destination = document.getElementById("destination").value.trim();
    const departure = document.getElementById("departure").value.trim() || "New York";
    const durationDays = Number.parseInt(
      document.getElementById("duration").value, 10
    );
    const budget = Number.parseFloat(
      document.getElementById("budget").value
    );
    const travelers = Number.parseInt(
      document.getElementById("travelers").value, 10
    );
    const hotelTier = document.getElementById("hotelTier").value;

    const preferences = Array.from(
      document.querySelectorAll('input[name="preferences"]:checked')
    ).map((checkbox) => checkbox.value);

    if (
      !destination ||
      !Number.isInteger(durationDays) ||
      durationDays < 1 ||
      durationDays > 14 ||
      !Number.isFinite(budget) ||
      budget < 200 ||
      !Number.isInteger(travelers) ||
      travelers < 1 ||
      travelers > 10
    ) {
      alert("Please enter valid trip details.");
      return;
    }

    const requestId = ++activePlanRequest;

    currentTripId = null;
    currentDestination = destination;
    currentDuration = durationDays;

    generateBtn.disabled = true;
    generateBtn.textContent = "⏳ DreamLine AI is planning your trip...";

    agentTracker.classList.add("active");
    resultsDashboard.classList.remove("active");

    resetAgentTracker();
    simulateAgentFlow();

    try {
      const response = await fetch("/api/trip/plan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          destination,
          departure_city: departure,
          duration_days: durationDays,
          budget,
          travelers_count: travelers,
          travel_preferences: preferences.length
            ? preferences
            : ["culture", "sightseeing"],
          accommodation_type: hotelTier,
          user_id: currentUserId
        })
      });

      if (!response.ok) {
        throw new Error(await getApiError(response));
      }

      const data = await response.json();

      if (!data.trip_id) {
        throw new Error("The server did not return a trip ID.");
      }

      if (requestId !== activePlanRequest) return;

      currentTripId = data.trip_id;

      clearAgentTimers();
      completeAllAgents();

      renderDashboard(data);

      resultsDashboard.classList.add("active");

      resultsDashboard.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });

    } catch (error) {
      if (requestId !== activePlanRequest) return;

      console.error("Trip planning failed:", error);

      alert(`Unable to generate itinerary: ${error.message}`);

      resetAgentTracker();
      agentTracker.classList.remove("active");

    } finally {
      if (requestId === activePlanRequest) {
        clearAgentTimers();
        generateBtn.disabled = false;
        generateBtn.textContent = "🚀 Generate Itinerary with DreamLine AI";
      }
    }
  });

  // PDF DOWNLOAD
  downloadPdfBtn.addEventListener("click", () => {
    if (!currentTripId) {
      alert("Please generate a trip plan first.");
      return;
    }

    const url = `/api/trip/${encodeURIComponent(currentTripId)}/pdf`;

    window.open(url, "_blank", "noopener,noreferrer");
  });

  // CHAT
  sendChatBtn.addEventListener("click", sendChatMessage);

  chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendChatMessage();
    }
  });

  async function sendChatMessage() {
    const message = chatInput.value.trim();

    if (!message || sendChatBtn.disabled) return;

    appendChatBubble("user", message);
    chatInput.value = "";

    sendChatBtn.disabled = true;
    sendChatBtn.textContent = "...";
    const typingIndicator = appendTypingIndicator();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          trip_id: currentTripId,
          user_id: currentUserId,
          destination: currentDestination,
          duration_days: currentDuration,
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

      typingIndicator.remove();
      appendChatBubble("assistant", data.reply);

      if (data.updated_plan) {
        currentTripId = data.updated_plan.trip_id || currentTripId;
        currentDestination = data.updated_plan.destination || currentDestination;
        currentDuration = data.updated_plan.duration_days || currentDuration;
        renderDashboard(data.updated_plan);
        resultsDashboard.classList.add("active");
      }

    } catch (error) {
      console.error("Chat failed:", error);

      appendChatBubble(
        "assistant",
        `Unable to get an AI response: ${error.message}`,
        "error"
      );

    } finally {
      typingIndicator.remove();
      sendChatBtn.disabled = false;
      sendChatBtn.textContent = "Send";
      chatInput.focus();
    }
  }

  function appendChatBubble(role, message, extraClass = "") {
    const bubble = document.createElement("div");

    bubble.className = `chat-bubble ${role} ${extraClass}`.trim();
    bubble.textContent = String(message ?? "");

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  function appendTypingIndicator() {
    const indicator = appendChatBubble(
      "assistant",
      "DreamLine AI is thinking...",
      "typing-indicator"
    );
    indicator.setAttribute("aria-label", "DreamLine AI is typing");
    return indicator;
  }

  // AGENT TRACKER
  function clearAgentTimers() {
    agentTimers.forEach(clearTimeout);
    agentTimers = [];
  }

  function resetAgentTracker() {
    clearAgentTimers();

    document.querySelectorAll(".agent-card").forEach((card) => {
      card.className = "agent-card";
      card.querySelector(".status-text").textContent = "Waiting...";
    });
  }

  function simulateAgentFlow() {
    const steps = [
      ["agent-manager", "Analyzing trip parameters..."],
      ["agent-dest", "Researching destinations..."],
      ["agent-weather", "Checking weather..."],
      ["agent-hotel", "Finding hotels..."],
      ["agent-budget", "Calculating budget..."],
      ["agent-itinerary", "Preparing itinerary..."]
    ];

    steps.forEach(([id, text], index) => {
      const timer = setTimeout(() => {
        const card = document.getElementById(id);

        if (!card) return;

        card.classList.add("running");
        card.querySelector(".status-text").textContent = text;
      }, index * 400);

      agentTimers.push(timer);
    });
  }

  function completeAllAgents() {
    document.querySelectorAll(".agent-card").forEach((card) => {
      card.className = "agent-card done";
      card.querySelector(".status-text").textContent = "Task Completed ✓";
    });
  }

  // UTILITIES
  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = String(value ?? "—");
  }

  function formatMoney(value) {
    const amount = Number(value);

    if (!Number.isFinite(amount)) return "—";

    return `$${amount.toLocaleString("en-US", {
      maximumFractionDigits: 2
    })}`;
  }

  function createElement(tag, className, text) {
    const element = document.createElement(tag);

    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);

    return element;
  }

  async function getApiError(response) {
    let message = `Server returned HTTP ${response.status}`;

    try {
      const data = await response.json();

      if (typeof data.detail === "string") {
        message = data.detail;
      }
    } catch {
      // Keep the HTTP status message.
    }

    return message;
  }

  // RESULTS DASHBOARD
  function renderDashboard(data) {
    setText(
      "resDestTitle",
      `${data.destination || currentDestination} (${data.duration_days || currentDuration} Days)`
    );

    setText("resBudgetVal", formatMoney(data.budget));
    setText("resTravelersVal", `${data.travelers ?? "—"} Guests`);

    // WEATHER
    const weather = data.weather_summary || {};

    const temperature = weather.temperature_celsius;

    const weatherText = temperature != null
      ? `${temperature}°C, ${weather.condition || "Condition unavailable"}`
      : (weather.condition || "Weather unavailable");

    setText("resWeatherVal", weatherText);
    setText(
      "resWeatherAdvisory",
      weather.travel_advisory || "No advisory available."
    );

    // BUDGET
    const budget = data.budget_breakdown || {};

    setText(
      "resFoodVal",
      formatMoney(budget.estimated_food_total_usd)
    );

    setText(
      "resTransitVal",
      formatMoney(budget.estimated_local_transit_usd)
    );

    setText(
      "resBufferVal",
      formatMoney(budget.emergency_buffer_usd)
    );

    // HOTELS
    const hotelsContainer = document.getElementById("resHotelsList");
    hotelsContainer.replaceChildren();

    const hotels = Array.isArray(data.hotels) ? data.hotels : [];

    if (!hotels.length) {
      hotelsContainer.appendChild(
        createElement("p", "empty-state", "No hotel recommendations available.")
      );
    }

    hotels.forEach((hotel) => {
      const card = createElement("div", "hotel-item");

      const name = createElement(
        "h4",
        "",
        hotel.name || "Hotel recommendation"
      );

      const details = createElement(
        "div",
        "hotel-details",
        `Area: ${hotel.area || "Not specified"} | ⭐ ${hotel.rating ?? "N/A"}`
      );

      const price = createElement(
        "div",
        "price",
        `${formatMoney(hotel.nightly_rate_usd)}/night | Total: ${formatMoney(hotel.total_stay_cost_usd)}`
      );

      const amenities = Array.isArray(hotel.amenities)
        ? hotel.amenities.join(", ")
        : "Not specified";

      const amenitiesElement = createElement(
        "div",
        "hotel-details",
        `Amenities: ${amenities}`
      );

      card.append(name, details, price, amenitiesElement);
      hotelsContainer.appendChild(card);
    });

    // DAILY ITINERARY
    const timeline = document.getElementById("resTimeline");
    timeline.replaceChildren();

    const days = Array.isArray(data.daily_itinerary)
      ? data.daily_itinerary
      : [];

    if (!days.length) {
      timeline.appendChild(
        createElement("p", "empty-state", "No itinerary details available.")
      );
    }

    days.forEach((day) => {
      const card = createElement("div", "day-card");

      const heading = createElement(
        "h3",
        "",
        `Day ${day.day ?? "—"}: ${day.title || "Exploring"}`
      );

      card.appendChild(heading);

      const slots = day.slots || {};

      [
        ["Morning", slots.morning],
        ["Afternoon", slots.afternoon],
        ["Evening", slots.evening]
      ].forEach(([label, activity]) => {
        const row = createElement("div", "slot-item");

        const tag = createElement("span", "slot-tag", label);
        const content = createElement(
          "div",
          "",
          activity || "No activity specified"
        );

        row.append(tag, content);
        card.appendChild(row);
      });

      timeline.appendChild(card);
    });
  }
});
