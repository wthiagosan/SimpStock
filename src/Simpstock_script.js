// Script da landing page (carrossel e navegação)
let currentIndex = 0;

function updateCarousel() {
    const images = document.querySelectorAll('.carousel-images img');
    if (!images.length) return;
    const totalImages = images.length;
    const visibleImages = 3;
    const maxIndex = totalImages - visibleImages;
    if (currentIndex > maxIndex) currentIndex = maxIndex;
    if (currentIndex < 0) currentIndex = 0;
    const offset = currentIndex * (100 / visibleImages);
    images.forEach(img => {
        img.style.transform = `translateX(-${offset * totalImages / visibleImages}%)`;
    });
}

function nextSlide() {
    const images = document.querySelectorAll('.carousel-images img');
    const maxIndex = images.length - 3;
    if (currentIndex < maxIndex) {
        currentIndex++;
        updateCarousel();
    }
}

function prevSlide() {
    if (currentIndex > 0) {
        currentIndex--;
        updateCarousel();
    }
}
