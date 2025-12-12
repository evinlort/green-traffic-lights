const NEARBY_RADIUS_METERS = 5000;
const distanceText = document.getElementById('distance-text');
const mapStatus = document.getElementById('map-status');
const mapContainer = document.getElementById('map');

const STATUS_CLASSES = ['status--info', 'status--success', 'status--warning', 'status--error'];

let mapInstance = null;
let userMarker = null;
let lightMarkers = [];

function setStatus(target, text, state = 'info') {
  if (!target) return;

  target.textContent = text;
  target.classList.remove(...STATUS_CLASSES);
  if (state) {
    target.classList.add(`status--${state}`);
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
      label: (item.LightNumber ?? item.LightNumbe)?.toString().trim() || 'Светофор (ID отсутствует)',
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

function clearLightMarkers() {
  lightMarkers.forEach((marker) => marker.setMap(null));
  lightMarkers = [];
}

function createMarker(googleMaps, light, isHighlighted = false) {
  const marker = new googleMaps.Marker({
    position: { lat: light.lat, lng: light.lon },
    map: mapInstance,
    title: `Светофор ${light.label}`,
    icon: isHighlighted
      ? {
          path: googleMaps.SymbolPath.BACKWARD_CLOSED_ARROW,
          scale: 6,
          fillColor: '#22c55e',
          fillOpacity: 1,
          strokeColor: '#064e3b',
          strokeWeight: 2,
        }
      : {
          path: googleMaps.SymbolPath.BACKWARD_CLOSED_ARROW,
          scale: 4,
          fillColor: '#fbbf24',
          fillOpacity: 1,
          strokeColor: '#1f2937',
          strokeWeight: 1,
        },
    zIndex: isHighlighted ? 20 : 5,
    animation: isHighlighted ? googleMaps.Animation.DROP : null,
    ariaLabel: `Светофор ${light.label}`,
  });

  lightMarkers.push(marker);
  return marker;
}

function findNearestLight(userPosition, lights) {
  return lights.reduce(
    (acc, light) => {
      const distance = haversineDistanceMeters(
        { lat: userPosition.lat, lon: userPosition.lng },
        { lat: light.lat, lon: light.lon },
      );

      if (distance > 0 && distance < acc.bestDistance) {
        return { bestDistance: distance, light: { ...light, distance } };
      }
      return acc;
    },
    { bestDistance: Number.POSITIVE_INFINITY, light: null },
  ).light;
}

function fitMapToBounds(googleMaps, points) {
  if (!mapInstance || points.length === 0) return;

  const bounds = new googleMaps.LatLngBounds();
  points.forEach((point) => bounds.extend({ lat: point.lat, lng: point.lng }));
  mapInstance.fitBounds(bounds, { top: 24, bottom: 24, left: 24, right: 24 });
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

  setStatus(distanceText, message, 'error');
  setStatus(mapStatus, message, 'error');
}

function requestCurrentPosition(options) {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, options);
  });
}

async function initGreenWay() {
  try {
    if (!mapContainer) {
      throw new Error('Контейнер карты не найден на странице.');
    }

    if (!navigator.geolocation) {
      setStatus(distanceText, 'Браузер не поддерживает геолокацию.', 'error');
      setStatus(mapStatus, 'Ваш браузер не поддерживает геолокацию.', 'error');
      return;
    }

    setStatus(distanceText, 'Запрашиваем геолокацию…', 'info');
    setStatus(mapStatus, 'Подготовка карты…', 'info');

    const apiKey = window.GOOGLE_MAPS_API_KEY || '';
    const [googleMaps, lights] = await Promise.all([
      loadGoogleMaps(apiKey),
      fetchTrafficLights(),
    ]);

    let position;
    try {
      position = await requestCurrentPosition({ enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
    } catch (geoError) {
      handleGeolocationError(geoError);
      return;
    }
    const { latitude, longitude } = position.coords;
    const userLocation = { lat: latitude, lng: longitude };

    mapInstance = new googleMaps.Map(mapContainer, {
      center: userLocation,
      zoom: 15,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
    });

    placeUserMarker(googleMaps, userLocation);

    const lightsWithDistance = lights
      .map((light) => ({
        ...light,
        distance: haversineDistanceMeters(userLocation, { lat: light.lat, lon: light.lon }),
      }))
      .filter((light) => Number.isFinite(light.distance) && light.distance <= NEARBY_RADIUS_METERS && light.distance > 0);

    clearLightMarkers();
    lightsWithDistance.forEach((light) => createMarker(googleMaps, light));

    const nearest = findNearestLight(userLocation, lightsWithDistance);

    if (nearest) {
      createMarker(googleMaps, nearest, true);
      setStatus(
        distanceText,
        `До ближайшего зелёного светофора: ${formatDistance(nearest.distance)}`,
        'success',
      );
      setStatus(mapStatus, 'Показаны светофоры в радиусе 5 км от вас.', 'success');
    } else if (lights.length === 0) {
      setStatus(distanceText, 'Нет данных о светофорах для расчёта расстояния.', 'warning');
      setStatus(mapStatus, 'Добавьте точки светофоров в light_traffics.json.', 'warning');
    } else {
      setStatus(distanceText, 'Нет светофоров в радиусе 5 км.', 'warning');
      setStatus(mapStatus, 'Попробуйте переместиться ближе к известным точкам.', 'warning');
    }

    fitMapToBounds(googleMaps, [userLocation, ...lightsWithDistance]);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Ошибка инициализации карты.';
    console.error('Ошибка в сценарии green_way:', error);
    setStatus(distanceText, message, 'error');
    setStatus(mapStatus, message, 'error');
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initGreenWay);
} else {
  initGreenWay();
}
