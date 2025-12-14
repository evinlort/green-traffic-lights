const STATES = [
  'requesting',
  'sending',
  'success',
  'error',
];

const button = document.getElementById('go-button');
const statusEl = document.getElementById('status');

function setDisabled(flag) {
  if (button) {
    button.disabled = !!flag;
  }
}

function setStatus(text = '', state = null) {
  if (statusEl) {
    statusEl.textContent = text;
  }

  if (!button) return;

  button.classList.add('go-button');
  STATES.forEach((s) => button.classList.remove(`go-button--${s}`));

  if (state && STATES.includes(state)) {
    button.classList.add(`go-button--${state}`);
  }
}

function handleGeolocationError(error) {
  let message = 'Не удалось получить геолокацию. Попробуйте ещё раз.';

  if (error.code === error.PERMISSION_DENIED) {
    message = 'Доступ к геолокации запрещён. Разрешите доступ в настройках браузера.';
  } else if (error.code === error.POSITION_UNAVAILABLE) {
    message = 'Сервис геолокации недоступен. Проверьте подключение или настройки.';
  } else if (error.code === error.TIMEOUT) {
    message = 'Запрос геолокации завершился по таймауту. Попробуйте снова.';
  }

  setStatus(message, 'error');
  stopTracking();
}

const TRAFFIC_LIGHT_RADIUS = 1000; // meters
const PASS_RADIUS = 50; // meters around the light to evaluate pass state
const BASE_INTERVAL_MS = 5000;
const POSITION_HISTORY_LIMIT = 3;
const SPEED_DROP_THRESHOLD_KMH = 5; // minimum drop to mark red

const trackingSession = {
  isTracking: false,
  trafficLights: [],
  positionHistory: [],
  pollingTimeoutId: null,
  previousAverageSpeed: null,
};

function toRadians(degrees) {
  return degrees * (Math.PI / 180);
}

function haversineDistanceMeters(lat1, lon1, lat2, lon2) {
  const earthRadius = 6371e3;
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return earthRadius * c;
}

async function loadTrafficLights() {
  try {
    const response = await fetch('/light_traffics.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const raw = await response.json();
    trackingSession.trafficLights = raw
      .map((item) => ({
        lat: Number.parseFloat(item.lat),
        lon: Number.parseFloat(item.lon),
      }))
      .filter((item) => Number.isFinite(item.lat) && Number.isFinite(item.lon));
    return trackingSession.trafficLights.length > 0;
  } catch (error) {
    console.error('Не удалось загрузить координаты светофоров', error);
    trackingSession.trafficLights = [];
    return false;
  }
}

function getNearestLightDistance(lat, lon) {
  if (!trackingSession.trafficLights.length) return null;

  return trackingSession.trafficLights.reduce((minDistance, light) => {
    const distance = haversineDistanceMeters(lat, lon, light.lat, light.lon);
    return Math.min(minDistance, distance);
  }, Number.POSITIVE_INFINITY);
}

function addPositionToHistory(position) {
  const history = trackingSession.positionHistory;
  history.push(position);
  if (history.length > POSITION_HISTORY_LIMIT) {
    trackingSession.positionHistory = history.slice(-POSITION_HISTORY_LIMIT);
  }
}

function computeAverageSpeedKmh(history) {
  if (history.length < 2) {
    return history[history.length - 1]?.speed ?? null;
  }

  let totalDistance = 0;
  let totalTimeSeconds = 0;

  for (let i = 1; i < history.length; i += 1) {
    const prev = history[i - 1];
    const current = history[i];
    const distance = haversineDistanceMeters(prev.lat, prev.lon, current.lat, current.lon);
    const timeDiffSeconds = (current.timestamp - prev.timestamp) / 1000;
    if (timeDiffSeconds > 0) {
      totalDistance += distance;
      totalTimeSeconds += timeDiffSeconds;
    }
  }

  if (totalTimeSeconds === 0) return null;
  return (totalDistance / totalTimeSeconds) * 3.6;
}

function determineState(distanceToLight, averageSpeed, previousAverageSpeed) {
  let state = 'tracking';

  if (distanceToLight != null && distanceToLight <= PASS_RADIUS && averageSpeed != null) {
    const speedDrop = previousAverageSpeed != null ? previousAverageSpeed - averageSpeed : 0;
    state = speedDrop >= SPEED_DROP_THRESHOLD_KMH ? 'red' : 'green';
  }

  const nextPreviousAverageSpeed = averageSpeed != null ? averageSpeed : previousAverageSpeed;

  return { state, nextPreviousAverageSpeed };
}

function calculateIntervalMs(distanceToLight) {
  if (distanceToLight == null) return BASE_INTERVAL_MS;

  if (distanceToLight > TRAFFIC_LIGHT_RADIUS) {
    return BASE_INTERVAL_MS;
  }

  const adjustedDistance = Math.max(distanceToLight, 0);
  const steps = Math.ceil(adjustedDistance / 100) || 1;
  const intervalSeconds = Math.max(0.5, steps * 0.5);
  return intervalSeconds * 1000;
}

function stopTracking() {
  if (trackingSession.pollingTimeoutId) {
    clearTimeout(trackingSession.pollingTimeoutId);
    trackingSession.pollingTimeoutId = null;
  }
  trackingSession.positionHistory = [];
  trackingSession.previousAverageSpeed = null;
  trackingSession.isTracking = false;
  setDisabled(false);
}

function scheduleNextPoll(distanceToLight) {
  const nextInterval = calculateIntervalMs(distanceToLight);
  trackingSession.pollingTimeoutId = setTimeout(() => {
    navigator.geolocation.getCurrentPosition(handleSuccess, handleGeolocationError, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });
  }, nextInterval);
}

async function sendPayload(payload) {
  setStatus('Отправляем данные…', 'sending');

  try {
    const response = await fetch('/api/click', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      setStatus('Сигнал отправлен! Спасибо.', 'success');
      return;
    }

    let responseBody = null;
    try {
      responseBody = await response.json();
    } catch (parseError) {
      // Ignore JSON parsing failures for non-JSON responses
    }

    const backendError = responseBody && typeof responseBody.error === 'string'
      ? responseBody.error
      : `HTTP ${response.status}`;
    throw new Error(backendError);
  } catch (err) {
    console.error('Ошибка при отправке данных', err);
    const message = typeof err === 'string'
      ? err
      : err instanceof Error && err.message
        ? err.message
        : 'Не удалось отправить данные. Попробуйте ещё раз.';
    setStatus(message, 'error');
    stopTracking();
  }
}

function handleSuccess(position) {
  if (!trackingSession.isTracking) return;

  const { latitude: lat, longitude: lon, speed } = position.coords;
  const timestampMs = position.timestamp;
  const speedKmh = Number.isFinite(speed) ? speed * 3.6 : null;

  const point = {
    lat,
    lon,
    speed: speedKmh,
    timestamp: timestampMs,
  };

  addPositionToHistory(point);

  const averageSpeed = computeAverageSpeedKmh(trackingSession.positionHistory);
  const distanceToLight = getNearestLightDistance(lat, lon);
  const { state, nextPreviousAverageSpeed } = determineState(
    distanceToLight,
    averageSpeed,
    trackingSession.previousAverageSpeed,
  );
  trackingSession.previousAverageSpeed = nextPreviousAverageSpeed;

  const payload = {
    lat,
    lon,
    speed: averageSpeed,
    state,
    timestamp: new Date(timestampMs).toISOString(),
  };

  sendPayload(payload);

  scheduleNextPoll(distanceToLight);
}

function handleClick() {
  if (!navigator.geolocation) {
    setStatus('Ваш браузер не поддерживает геолокацию.', 'error');
    return;
  }

  if (trackingSession.isTracking) {
    setStatus('Уже отслеживаем положение…', 'requesting');
    return;
  }

  trackingSession.isTracking = true;
  setDisabled(true);
  setStatus('Запрашиваем геолокацию…', 'requesting');
  loadTrafficLights()
    .then((loaded) => {
      if (!loaded) {
        setStatus('Не удалось загрузить координаты светофоров. Попробуйте позже.', 'error');
        stopTracking();
        return;
      }

      navigator.geolocation.getCurrentPosition(handleSuccess, handleGeolocationError, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      });
    })
    .catch(() => {
      setStatus('Не удалось загрузить координаты светофоров. Попробуйте позже.', 'error');
      stopTracking();
    });
}

if (button) {
  button.addEventListener('click', handleClick);
}

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch((err) => {
      console.error('Service worker registration failed', err);
    });
  });
}

setStatus();
