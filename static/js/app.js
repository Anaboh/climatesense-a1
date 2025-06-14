// Progressive Web App functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered:', registration);
            })
            .catch(error => {
                console.log('Service Worker registration failed:', error);
            });
    });
}

// Handle PWA install prompt
let deferredPrompt;
const installContainer = document.getElementById('installContainer');
const installBtn = document.getElementById('installBtn');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installContainer.style.display = 'block';
});

installBtn.addEventListener('click', () => {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(choiceResult => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted install');
            } else {
                console.log('User dismissed install');
            }
            deferredPrompt = null;
            installContainer.style.display = 'none';
        });
    }
});

// Check if app is running in standalone mode
window.addEventListener('load', () => {
    if (window.matchMedia('(display-mode: standalone)').matches) {
        installContainer.style.display = 'none';
    }
});
