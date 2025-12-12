const NEARBY_RADIUS_METERS = 50;
const NEARBY_RADIUS_TEXT =
  NEARBY_RADIUS_METERS % 1000 === 0
    ? `${NEARBY_RADIUS_METERS / 1000} км`
    : `${NEARBY_RADIUS_METERS} м`;
const distanceText = document.getElementById('distance-text');
const mapStatus = document.getElementById('map-status');
const mapContainer = document.getElementById('map');

let mapInstance = null;
let userMarker = null;
let lightMarkers = [];
let refreshIntervalId = null;

function cleanupRefreshInterval() {
  if (refreshIntervalId !== null) {
    clearInterval(refreshIntervalId);
    refreshIntervalId = null;
  }
}

function setStatus(target, text, state = 'info') {
  if (!target) return;

  target.textContent = text;
  Array.from(target.classList)
    .filter((className) => className.startsWith('status--'))
    .forEach((className) => target.classList.remove(className));
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

  const markerPosition = { lat: position.lat, lng: position.lon };

  if (userMarker) {
    userMarker.setPosition(markerPosition);
    return;
  }

  userMarker = new googleMaps.Marker({
    position: markerPosition,
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
  const baseIcon = {
    path: googleMaps.SymbolPath.BACKWARD_CLOSED_ARROW,
    fillOpacity: 1,
  };

  const icon = isHighlighted
    ? {
        ...baseIcon,
        scale: 6,
        fillColor: '#22c55e',
        strokeColor: '#064e3b',
        strokeWeight: 2,
      }
    : {
        ...baseIcon,
        scale: 4,
        fillColor: '#fbbf24',
        strokeColor: '#1f2937',
        strokeWeight: 1,
      };

  const marker = new googleMaps.Marker({
    position: { lat: light.lat, lng: light.lon },
    map: mapInstance,
    title: `Светофор ${light.label}`,
    icon,
    zIndex: isHighlighted ? 20 : 5,
    animation: isHighlighted ? googleMaps.Animation.DROP : null,
    ariaLabel: `Светофор ${light.label}`,
  });

  lightMarkers.push(marker);
  return marker;
}

function findNearestLight(lights) {
  return lights.reduce(
    (nearest, light) =>
      light.distance > 0 && light.distance < (nearest?.distance ?? Infinity) ? light : nearest,
    null,
  );
}

function fitMapToBounds(googleMaps, points) {
  if (!mapInstance || points.length === 0) return;

  const bounds = new googleMaps.LatLngBounds();
  points.forEach((point) => {
    const lng = point.lon ?? point.lng;
    if (Number.isFinite(point.lat) && Number.isFinite(lng)) {
      bounds.extend({ lat: point.lat, lng });
    }
  });

  if (!bounds.isEmpty()) {
    mapInstance.fitBounds(bounds, { top: 24, bottom: 24, left: 24, right: 24 });
  }
}

function shouldRefitMap(googleMaps, points) {
  if (!mapInstance) return false;
  const bounds = mapInstance.getBounds();
  if (!bounds || bounds.isEmpty()) return true;

  return points.some((point) => {
    const lng = point.lon ?? point.lng;
    if (!Number.isFinite(point.lat) || !Number.isFinite(lng)) return false;
    return !bounds.contains(new googleMaps.LatLng(point.lat, lng));
  });
}

function showNearestLightStatus(nearest) {
  setStatus(
    distanceText,
    `До ближайшего зелёного светофора: ${formatDistance(nearest.distance)}`,
    'success',
  );
  setStatus(mapStatus, `Показаны светофоры в радиусе ${NEARBY_RADIUS_TEXT} от вас.`, 'success');
}

function showNoLightsDataStatus() {
  setStatus(distanceText, 'Нет данных о светофорах для расчёта расстояния.', 'warning');
  setStatus(mapStatus, 'Добавьте точки светофоров в light_traffics.json.', 'warning');
}

function showNoNearbyLightsStatus() {
  setStatus(distanceText, `Нет светофоров в радиусе ${NEARBY_RADIUS_TEXT}.`, 'warning');
  setStatus(mapStatus, 'Попробуйте переместиться ближе к известным точкам.', 'warning');
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

async function updateMapState(googleMaps, lights, { refitOnChange = false } = {}) {
  try {
    let position;
    try {
      position = await requestCurrentPosition({ enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
    } catch (geoError) {
      handleGeolocationError(geoError);
      return;
    }

    const { latitude, longitude } = position.coords;
    const userLocation = { lat: latitude, lon: longitude };

    placeUserMarker(googleMaps, userLocation);

    const lightsWithDistance = lights
      .map((light) => ({
        ...light,
        distance: haversineDistanceMeters(
          { lat: userLocation.lat, lon: userLocation.lon },
          { lat: light.lat, lon: light.lon },
        ),
      }))
      .filter((light) => Number.isFinite(light.distance) && light.distance <= NEARBY_RADIUS_METERS && light.distance > 0);

    const nearest = findNearestLight(lightsWithDistance);

    clearLightMarkers();
    lightsWithDistance.forEach((light) => createMarker(googleMaps, light, light === nearest));

    if (nearest) {
      showNearestLightStatus(nearest);
    } else if (lights.length === 0) {
      showNoLightsDataStatus();
    } else {
      showNoNearbyLightsStatus();
    }

    if (refitOnChange) {
      const points = [userLocation, ...lightsWithDistance];
      if (shouldRefitMap(googleMaps, points)) {
        fitMapToBounds(googleMaps, points);
      }
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Ошибка при обновлении карты.';
    console.error('Ошибка обновления карты green_way:', error);
    setStatus(distanceText, message, 'error');
    setStatus(mapStatus, message, 'error');
  }
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
    const userLocation = { lat: latitude, lon: longitude };

    mapInstance = new googleMaps.Map(mapContainer, {
      center: { lat: userLocation.lat, lng: userLocation.lon },
      zoom: 15,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
    });

    await updateMapState(googleMaps, lights, { refitOnChange: true });

    cleanupRefreshInterval();
    refreshIntervalId = window.setInterval(
      () => updateMapState(googleMaps, lights, { refitOnChange: true }),
      5000,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Ошибка инициализации карты.';
    console.error('Ошибка в сценарии green_way:', error);
    setStatus(distanceText, message, 'error');
    setStatus(mapStatus, message, 'error');
  }
}

window.addEventListener('pagehide', cleanupRefreshInterval);
window.addEventListener('beforeunload', cleanupRefreshInterval);

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initGreenWay);
} else {
  initGreenWay();
}
