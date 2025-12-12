const distanceText = document.getElementById('distance-text');
const mapStatus = document.getElementById('map-status');
const mapContainer = document.getElementById('map');
let mapInstance = null;
let userMarker = null;

function updateDistanceText(text) {
  if (distanceText) {
    distanceText.textContent = text;
  }
}

function updateMapStatus(text) {
  if (mapStatus) {
    mapStatus.textContent = text;
  }
}

function toRadians(value) {
  return (value * Math.PI) / 180;
}

function haversineDistanceMeters(a, b) {
  const R = 6371000;
  const dLat = toRadians(b.lat - a.lat);
  const dLon = toRadians(b.lon - a.lon);
  const lat1 = toRadians(a.lat);
  const lat2 = toRadians(b.lat);

  const sinLat = Math.sin(dLat / 2);
  const sinLon = Math.sin(dLon / 2);
  const h = sinLat * sinLat + Math.cos(lat1) * Math.cos(lat2) * sinLon * sinLon;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function formatDistance(meters) {
  if (!Number.isFinite(meters)) return '—';
  if (meters < 1000) {
    return `${Math.round(meters)} м`;
  }
  return `${(meters / 1000).toFixed(2)} км`;
}

async function loadGoogleMaps(apiKey) {
  if (window.google?.maps) {
    return window.google.maps;
  }

  if (!apiKey) {
    throw new Error(
      'Отсутствует ключ API Google Maps. Установите GOOGLE_MAPS_API_KEY перед запуском приложения.',
    );
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google?.maps) {
        resolve(window.google.maps);
      } else {
        reject(new Error('Не удалось инициализировать Google Maps.'));
      }
    };
    script.onerror = () => reject(new Error('Ошибка при загрузке Google Maps.'));
    document.head.appendChild(script);
  });
}

async function fetchTrafficLights() {
  const response = await fetch('/light_traffics.json');
  if (!response.ok) {
    throw new Error(`Не удалось загрузить данные светофоров: HTTP ${response.status}`);
  }

  const rawData = await response.json();
  return rawData
    .map((item) => ({
      lat: Number.parseFloat(item.lat),
      lon: Number.parseFloat(item.lon),
      label:
        (item.LightNumber ?? item.LightNumbe)?.toString().trim() || 'Светофор (ID отсутствует)',
    }))
    .filter((item) => Number.isFinite(item.lat) && Number.isFinite(item.lon));
}

function placeUserMarker(googleMaps, position) {
  if (!mapInstance) return;

  if (userMarker) {
    userMarker.setPosition(position);
    return;
  }

  userMarker = new googleMaps.Marker({
    position,
    map: mapInstance,
    title: 'Ваше местоположение',
    icon: {
      path: googleMaps.SymbolPath.CIRCLE,
      scale: 8,
      fillColor: '#34d399',
      fillOpacity: 1,
      strokeWeight: 2,
      strokeColor: '#0f172a',
    },
  });
}

function renderTrafficLightMarkers(googleMaps, lights) {
  if (!mapInstance) return;

  lights.forEach((light) => {
    new googleMaps.Marker({
      position: { lat: light.lat, lng: light.lon },
      map: mapInstance,
      title: `Светофор ${light.label}`,
      icon: {
        path: googleMaps.SymbolPath.BACKWARD_CLOSED_ARROW,
        scale: 4,
        fillColor: '#fbbf24',
        fillOpacity: 1,
        strokeColor: '#1f2937',
        strokeWeight: 1,
      },
      ariaLabel: `Светофор ${light.label}`,
    });
  });
}

function findNearestLight(userPosition, lights) {
  let nearest = null;
  let bestDistance = Number.POSITIVE_INFINITY;

  lights.forEach((light) => {
    const distance = haversineDistanceMeters(
      { lat: userPosition.lat, lon: userPosition.lng },
      { lat: light.lat, lon: light.lon },
    );

    if (distance > 0 && distance < bestDistance) {
      bestDistance = distance;
      nearest = { ...light, distance };
    }
  });

  return nearest;
}

function handleGeolocationError(error) {
  let message = 'Не удалось получить геолокацию. Разрешите доступ и попробуйте снова.';

  if (error.code === error.PERMISSION_DENIED) {
    message = 'Доступ к геолокации запрещён. Разрешите доступ в настройках браузера.';
  } else if (error.code === error.POSITION_UNAVAILABLE) {
    message = 'Сервис геолокации недоступен. Проверьте подключение к сети.';
  } else if (error.code === error.TIMEOUT) {
    message = 'Запрос геолокации превысил время ожидания. Попробуйте ещё раз.';
  }

  updateDistanceText(message);
  updateMapStatus(message);
}

async function initGreenWay() {
  try {
    const apiKey = window.GOOGLE_MAPS_API_KEY || '';
    const [googleMaps, lights] = await Promise.all([
      loadGoogleMaps(apiKey),
      fetchTrafficLights(),
    ]);

    if (!navigator.geolocation) {
      updateDistanceText('Браузер не поддерживает геолокацию.');
      return;
    }

    if (!mapContainer) {
      throw new Error('Контейнер карты не найден на странице.');
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const center = { lat: latitude, lng: longitude };

        mapInstance = new googleMaps.Map(mapContainer, {
          center,
          zoom: 15,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        });

        placeUserMarker(googleMaps, center);
        renderTrafficLightMarkers(googleMaps, lights);

        const nearest = findNearestLight(center, lights);
        if (nearest) {
          updateDistanceText(`До ближайшего зелёного светофора: ${formatDistance(nearest.distance)}`);
          updateMapStatus('Маршрут построен по вашему текущему местоположению.');
        } else {
          updateDistanceText('Нет данных о светофорах для расчёта расстояния.');
          updateMapStatus('Добавьте точки светофоров в light_traffics.json.');
        }
      },
      handleGeolocationError,
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Ошибка инициализации карты.';
    updateDistanceText(message);
    updateMapStatus(message);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initGreenWay);
} else {
  initGreenWay();
}
