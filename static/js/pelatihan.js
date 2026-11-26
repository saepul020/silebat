document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('sertifikat-modal');
    if (!modal || typeof modal.showModal !== 'function') {
        return;
    }

    const title = modal.querySelector('#sertifikat-title');
    const image = modal.querySelector('[data-sertifikat-image]');
    const frame = modal.querySelector('[data-sertifikat-frame]');
    const link = modal.querySelector('[data-sertifikat-link]');
    let trigger = null;

    document.querySelectorAll('[data-sertifikat-open]').forEach(function (button) {
        button.addEventListener('click', function (event) {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
                return;
            }
            const url = new URL(button.href, window.location.href);
            const fileName = button.dataset.fileName || '';
            const isImage = /\.(jpe?g|png)$/i.test(fileName);
            if (!isImage && !/\.pdf$/i.test(fileName)) {
                return;
            }

            event.preventDefault();
            trigger = button;
            title.textContent = 'Sertifikat — ' + button.dataset.peserta;
            image.hidden = !isImage;
            frame.hidden = isImage;
            if (isImage) {
                image.src = url.href;
                image.alt = 'Sertifikat ' + button.dataset.peserta;
            } else {
                frame.src = url.href;
            }
            link.href = url.href;
            modal.showModal();
        });
    });

    modal.querySelector('[data-sertifikat-close]').addEventListener('click', function () {
        modal.close();
    });

    modal.addEventListener('click', function (event) {
        const rect = modal.getBoundingClientRect();
        if (event.target === modal && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) {
            modal.close();
        }
    });

    modal.addEventListener('close', function () {
        image.removeAttribute('src');
        image.alt = '';
        image.hidden = true;
        frame.removeAttribute('src');
        frame.hidden = true;
        link.removeAttribute('href');
        if (trigger) {
            trigger.focus();
            trigger = null;
        }
    });
});
