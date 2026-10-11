
const profileForm = document.getElementById("profileForm");
const logForm = document.getElementById("logForm");
const message = document.getElementById("message");

function showMessage(text, type = "success") {
    message.textContent = text;
    message.className = "message " + type;
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
    }

    return data;
}

function fillList(elementId, items) {
    const list = document.getElementById(elementId);
    list.replaceChildren();

    items.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
    });
}

function displayProfile(data) {
    if (!data || !data.profile) return;

    const profile = data.profile;
    const plan = data.recommendations;

    document.getElementById("name").value = profile.name;
    document.getElementById("age").value = profile.age;
    document.getElementById("sex").value = profile.sex;
    document.getElementById("height").value = profile.height;
    document.getElementById("weight").value = profile.weight;
    document.getElementById("goal").value = profile.goal;
    document.getElementById("activity").value = profile.activity;
    document.getElementById("diet").value = profile.diet;

    document.getElementById("caloriesTarget").textContent =
        plan.calories.toLocaleString();

    document.getElementById("waterTarget").textContent = plan.water;
    document.getElementById("bmiTarget").textContent = plan.bmi;

    fillList("mealList", plan.meals);
    fillList("workoutList", plan.workouts);

    document.getElementById("recommendations").classList.remove("hidden");
    document.getElementById("tracker").classList.remove("hidden");
}

profileForm.addEventListener("submit", async event => {
    event.preventDefault();

    const formData = new FormData(profileForm);
    const profile = Object.fromEntries(formData.entries());

    try {
        const data = await apiRequest("/api/profile", {
            method: "POST",
            body: JSON.stringify(profile)
        });

        displayProfile(data);
        await loadLogs();
        showMessage("Your personalized plan is ready!");
        document.getElementById("recommendations").scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    } catch (error) {
        showMessage(error.message, "error");
    }
});

logForm.addEventListener("submit", async event => {
    event.preventDefault();

    const formData = new FormData(logForm);
    const values = Object.fromEntries(formData.entries());

    values.calories = Number(values.calories);
    values.workout_minutes = Number(values.workout_minutes);
    values.water = Number(values.water);
    values.weight = Number(values.weight);

    try {
        await apiRequest("/api/logs", {
            method: "POST",
            body: JSON.stringify(values)
        });

        document.getElementById("food").value = "";
        document.getElementById("logCalories").value = "0";
        document.getElementById("workout").value = "";
        document.getElementById("minutes").value = "0";
        document.getElementById("water").value = "0";
        document.getElementById("logWeight").value = "0";

        await loadLogs();
        showMessage("Your daily progress has been saved!");
    } catch (error) {
        showMessage(error.message, "error");
    }
});

async function loadLogs() {
    const data = await apiRequest("/api/logs");

    document.getElementById("totalCalories").textContent =
        Number(data.totals.calories).toLocaleString();

    document.getElementById("totalMinutes").textContent =
        data.totals.workout_minutes;

    document.getElementById("totalWater").textContent =
        Number(data.totals.water).toFixed(1);

    const table = document.getElementById("logsTable");
    table.replaceChildren();

    if (data.logs.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 5;
        cell.textContent = "No records yet.";
        row.appendChild(cell);
        table.appendChild(row);
    } else {
        data.logs.forEach(log => {
            const row = document.createElement("tr");

            [
                log.food || "—",
                log.calories,
                log.workout || "—",
                log.workout_minutes,
                Number(log.water).toFixed(1) + " L"
            ].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            table.appendChild(row);
        });
    }

    drawChart(data.weekly);
}

function drawChart(weekly) {
    const chart = document.getElementById("weeklyChart");
    chart.replaceChildren();

    const maximum = Math.max(
        1,
        ...weekly.map(day => Number(day.calories))
    );

    weekly.forEach(day => {
        const item = document.createElement("div");
        item.className = "chart-item";

        const value = document.createElement("span");
        value.className = "chart-value";
        value.textContent = day.calories;

        const bar = document.createElement("div");
        bar.className = "chart-bar";
        bar.style.height =
            Math.max(3, (Number(day.calories) / maximum) * 95) + "px";
        bar.title = day.date + ": " + day.calories + " kcal";

        const label = document.createElement("span");
        label.className = "chart-label";
        label.textContent = day.day;

        item.append(value, bar, label);
        chart.appendChild(item);
    });
}

async function initializeApp() {
    try {
        const data = await apiRequest("/api/profile");

        if (data.profile) {
            displayProfile(data);
            await loadLogs();
        }
    } catch (error) {
        showMessage("Could not load saved data. Please refresh the page.", "error");
    }
}

initializeApp();
