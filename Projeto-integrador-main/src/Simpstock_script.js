// Carrossel de Clientes
let currentSlide = 0;

function showSlide(index) {
    const slides = document.querySelectorAll('.carousel-images img');
    const totalSlides = slides.length;

    // Garantir que o índice seja cíclico
    if (index >= totalSlides / 3) currentSlide = 0;
    if (index < 0) currentSlide = Math.ceil(totalSlides / 3) - 1;

    // Atualizar a posição das imagens
    const offset = -currentSlide * 900; // 900px (300px por imagem * 3 imagens visíveis)
    slides.forEach(slide => {
        slide.style.transform = `translateX(${offset}px)`;
    });
}

function nextSlide() {
    currentSlide++;
    showSlide(currentSlide);
}

function prevSlide() {
    currentSlide--;
    showSlide(currentSlide);
}

// Login animação container
const container = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn = document.getElementById('login');

registerBtn.addEventListener('click', () => {
    container.classList.add("active");
});

loginBtn.addEventListener('click', () => {
    container.classList.remove("active");
});

// Validação de formulário
function isValidEmail(email) {
    // Expressão regular simples para validação de e-mail
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidPassword(password) {
    // Pelo menos uma letra e um número, com 6 ou mais caracteres
    return /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$/.test(password);
}

function validateForm(event) {
    const form = event.target;
    const email = form.querySelector('input[type="email"]').value;
    const password = form.querySelector('input[type="password"]').value;

    if (!isValidEmail(email)) {
        alert("Por favor, insira um e-mail válido.");
        event.preventDefault();
        return;
    }

    if (!isValidPassword(password)) {
        alert("A senha deve conter ao menos 6 caracteres, incluindo letras e números.");
        event.preventDefault();
        return;
    }
}

// Aplica validação a ambos os formulários
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', validateForm);
    });
});
