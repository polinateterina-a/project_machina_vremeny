// static/js/main.js - Полная логика с маршрутом и боковой панелью
class RetroExcursionApp {
    constructor() {
        this.map = null;
        this.excursionData = null;
        this.locations = [];
        this.markers = [];
        this.currentLocationIndex = -1;
        this.routeLine = null;
        this.activeAudio = null;
        this.audioPlayer = document.getElementById('globalAudio');
        
        this.init();
    }

    async init() {
        this.initMap();
        this.setupAudioListeners();
        await this.loadExcursion(1);
    }

    initMap() {
        this.map = L.map('map', {
            center: [56.011, 92.853],
            zoom: 15,
            zoomControl: true
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap',
            className: 'retro-tiles'
        }).addTo(this.map);
    }

    setupAudioListeners() {
        this.audioPlayer.addEventListener('timeupdate', () => this.updateAudioProgress());
        this.audioPlayer.addEventListener('ended', () => this.onAudioEnded());
        this.audioPlayer.addEventListener('loadedmetadata', () => this.updateAudioTime());
    }

    async loadExcursion(excursionId) {
        try {
            const response = await fetch(`/api/excursions/${excursionId}/locations`);
            this.excursionData = await response.json();
            this.locations = this.excursionData.locations;
            
            this.renderSidebar();
            this.renderMapMarkers();
            this.drawRoute();
            this.updateMapInfo();
            
        } catch (error) {
            console.error('Ошибка загрузки:', error);
        }
    }

    renderSidebar() {
        const excursion = this.excursionData.excursion;
        
        // Блоки начала и конца
        document.getElementById('startDescription').textContent = excursion.start_description;
        document.getElementById('endDescription').textContent = excursion.end_description;
        
        // Кнопки аудио для начала и конца
        document.querySelector('#startAudioPlayer .mini-play-btn').addEventListener('click', 
            () => this.toggleSideAudio('start', excursion.start_audio));
        document.querySelector('#endAudioPlayer .mini-play-btn').addEventListener('click', 
            () => this.toggleSideAudio('end', excursion.end_audio));
        
        // Список локаций
        const listContainer = document.getElementById('locationsList');
        listContainer.innerHTML = '';
        
        this.locations.forEach((location, index) => {
            const li = document.createElement('li');
            li.className = 'location-item';
            li.innerHTML = `
                <div class="location-number">${index + 1}</div>
                <div class="location-info">
                    <div class="location-name">${location.name}</div>
                    <div class="location-address">${location.address}</div>
                </div>
            `;
            
            li.addEventListener('click', () => {
                this.selectLocation(index);
                this.openLocationModal(location);
            });
            
            listContainer.appendChild(li);
            location._sidebarElement = li;
        });
    }

    renderMapMarkers() {
        // Удаляем старые маркеры
        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];
        
        const coordinates = [];
        
        this.locations.forEach((location, index) => {
            const icon = this.createMarkerIcon(index + 1, false);
            
            const marker = L.marker([location.lat, location.lng], { icon })
                .addTo(this.map);
            
            marker.on('click', () => {
                this.selectLocation(index);
                this.openLocationModal(location);
            });
            
            marker.bindTooltip(location.name, {
                direction: 'top',
                className: 'marker-tooltip'
            });
            
            this.markers.push(marker);
            coordinates.push([location.lat, location.lng]);
        });
        
        // Подгоняем карту под все маркеры
        if (coordinates.length > 0) {
            const bounds = L.latLngBounds(coordinates);
            this.map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    drawRoute() {
        // Удаляем старую линию
        if (this.routeLine) {
            this.map.removeLayer(this.routeLine);
        }
        
        const coordinates = this.locations.map(loc => [loc.lat, loc.lng]);
        
        this.routeLine = L.polyline(coordinates, {
            color: '#5d3a1a',
            weight: 4,
            dashArray: '10, 10',
            className: 'route-line'
        }).addTo(this.map);
    }

    createMarkerIcon(number, isActive) {
        const className = isActive ? 'custom-marker active-marker' : 'custom-marker';
        return L.divIcon({
            className: className,
            html: `
                <div class="marker-pin">
                    <span class="marker-number">${number}</span>
                </div>
            `,
            iconSize: [40, 40],
            iconAnchor: [20, 40],
            popupAnchor: [0, -40]
        });
    }

    selectLocation(index) {
        if (this.currentLocationIndex === index) return;
        
        const prevIndex = this.currentLocationIndex;
        this.currentLocationIndex = index;
        
        // Обновляем маркеры
        if (prevIndex >= 0 && this.markers[prevIndex]) {
            this.markers[prevIndex].setIcon(this.createMarkerIcon(prevIndex + 1, false));
        }
        this.markers[index].setIcon(this.createMarkerIcon(index + 1, true));
        
        // Обновляем боковую панель
        this.locations.forEach((loc, i) => {
            if (loc._sidebarElement) {
                loc._sidebarElement.classList.toggle('active', i === index);
            }
        });
        
        // Центрируем карту
        this.map.setView([this.locations[index].lat, this.locations[index].lng], 16);
    }

    async openLocationModal(location) {
        // Загружаем полные данные если нужно
        let fullLocation = location;
        if (!location.description) {
            const response = await fetch(`/api/locations/${location.id}`);
            fullLocation = await response.json();
        }
        
        // Заполняем модальное окно
        document.getElementById('modalTitle').textContent = fullLocation.name;
        document.getElementById('modalAddress').textContent = '📍 ' + fullLocation.address;
        document.getElementById('modalYear').textContent = '📅 ' + fullLocation.year;
        document.getElementById('modalTags').textContent = '🏷️ ' + fullLocation.tags;
        document.getElementById('modalDescription').textContent = fullLocation.description;
        
        // Слайдер
        this.modalLocation = fullLocation;
        this.currentPhotoType = 'modern';
        document.getElementById('modalImage').src = '/static/' + fullLocation.modern_photo;
        document.getElementById('sliderLabel').textContent = 'Современный вид';
        document.getElementById('sliderToggle').textContent = '📸 Было';
        
        document.getElementById('sliderToggle').onclick = () => this.toggleSlider();
        
        // Аудио
        if (fullLocation.audio_file) {
            document.querySelector('.modal-audio').style.display = 'block';
            this.loadAudio(fullLocation.audio_file);
        } else {
            document.querySelector('.modal-audio').style.display = 'none';
        }
        
        // Показать модальное окно
        document.getElementById('locationModal').style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        // Закрытие
        document.querySelector('.modal-close').onclick = () => this.closeModal();
        document.getElementById('locationModal').onclick = (e) => {
            if (e.target === e.currentTarget) this.closeModal();
        };
    }

    toggleSlider() {
        const btn = document.getElementById('sliderToggle');
        const img = document.getElementById('modalImage');
        const label = document.getElementById('sliderLabel');
        
        if (this.currentPhotoType === 'modern') {
            img.src = '/static/' + this.modalLocation.historical_photo;
            label.textContent = 'Исторический вид';
            btn.textContent = '📸 Стало';
            this.currentPhotoType = 'historical';
        } else {
            img.src = '/static/' + this.modalLocation.modern_photo;
            label.textContent = 'Современный вид';
            btn.textContent = '📸 Было';
            this.currentPhotoType = 'modern';
        }
    }

    loadAudio(audioFile) {
        this.audioPlayer.src = '/static/' + audioFile;
        this.audioPlayer.load();
        document.getElementById('modalPlayBtn').textContent = '▶';
        document.getElementById('modalPlayBtn').classList.remove('playing');
        document.getElementById('modalProgress').style.width = '0%';
        document.getElementById('modalTime').textContent = '00:00 / 00:00';
        
        document.getElementById('modalPlayBtn').onclick = () => this.toggleModalAudio();
        document.getElementById('modalSeek').oninput = (e) => this.seekAudio(e);
    }

    toggleModalAudio() {
        if (this.audioPlayer.paused) {
            this.audioPlayer.play();
            document.getElementById('modalPlayBtn').textContent = '⏸';
            document.getElementById('modalPlayBtn').classList.add('playing');
        } else {
            this.audioPlayer.pause();
            document.getElementById('modalPlayBtn').textContent = '▶';
            document.getElementById('modalPlayBtn').classList.remove('playing');
        }
    }

    toggleSideAudio(type, audioFile) {
        if (this.audioPlayer.src.includes(audioFile) && !this.audioPlayer.paused) {
            this.audioPlayer.pause();
            this.updateAllPlayButtons(null);
            return;
        }
        
        this.audioPlayer.src = '/static/' + audioFile;
        this.audioPlayer.load();
        this.audioPlayer.play();
        this.updateAllPlayButtons(type);
    }

    updateAllPlayButtons(activeType) {
        document.querySelectorAll('.mini-play-btn').forEach(btn => {
            const type = btn.dataset.audio;
            if (type === activeType && !this.audioPlayer.paused) {
                btn.textContent = '⏸';
                btn.classList.add('playing');
            } else {
                btn.textContent = '▶';
                btn.classList.remove('playing');
            }
        });
    }

    seekAudio(event) {
        const seekTime = (event.target.value / 100) * this.audioPlayer.duration;
        this.audioPlayer.currentTime = seekTime;
    }

    updateAudioProgress() {
        const audio = this.audioPlayer;
        if (audio.duration) {
            const progress = (audio.currentTime / audio.duration) * 100;
            document.getElementById('modalProgress').style.width = progress + '%';
            document.getElementById('modalSeek').value = progress;
            this.updateAudioTime();
        }
    }

    updateAudioTime() {
        const audio = this.audioPlayer;
        if (audio.duration) {
            const curMin = Math.floor(audio.currentTime / 60);
            const curSec = Math.floor(audio.currentTime % 60);
            const totMin = Math.floor(audio.duration / 60);
            const totSec = Math.floor(audio.duration % 60);
            
            const timeStr = `${String(curMin).padStart(2,'0')}:${String(curSec).padStart(2,'0')} / ${String(totMin).padStart(2,'0')}:${String(totSec).padStart(2,'0')}`;
            document.getElementById('modalTime').textContent = timeStr;
        }
    }

    onAudioEnded() {
        document.getElementById('modalPlayBtn').textContent = '▶';
        document.getElementById('modalPlayBtn').classList.remove('playing');
        this.updateAllPlayButtons(null);
    }

    closeModal() {
        this.audioPlayer.pause();
        this.audioPlayer.src = '';
        document.getElementById('locationModal').style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    updateMapInfo() {
        const ex = this.excursionData.excursion;
        document.getElementById('excursionTitle').textContent = ex.name;
        document.getElementById('excursionDuration').textContent = '⏱️ ' + ex.duration;
        document.getElementById('excursionDistance').textContent = '📏 ' + ex.distance;
        document.getElementById('excursionLocations').textContent = '📍 ' + this.locations.length + ' локации';
    }
}

// Запуск
document.addEventListener('DOMContentLoaded', () => {
    new RetroExcursionApp();
});