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
  setDisabled(false);
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
    const message = err instanceof Error && err.message
      ? err.message
      : 'Не удалось отправить данные. Попробуйте ещё раз.';
    setStatus(message, 'error');
  } finally {
    setDisabled(false);
  }
}

function handleSuccess(position) {
  const { latitude: lat, longitude: lon, speed } = position.coords;
  const speedKmh = Number.isFinite(speed) ? speed * 3.6 : null;

  const payload = {
    lat,
    lon,
    speed: speedKmh,
    timestamp: new Date().toISOString(),
  };

  sendPayload(payload);
}

function handleClick() {
  if (!navigator.geolocation) {
    setStatus('Ваш браузер не поддерживает геолокацию.', 'error');
    return;
  }

  setDisabled(true);
  setStatus('Запрашиваем геолокацию…', 'requesting');

  navigator.geolocation.getCurrentPosition(handleSuccess, handleGeolocationError, {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 0,
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
