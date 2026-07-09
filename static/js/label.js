(function () {
    const modal = document.querySelector("[data-master-preview-modal]");
    const openButtons = document.querySelectorAll("[data-master-preview-open]");

    if (!modal || !openButtons.length) {
        return;
    }

    const title = modal.querySelector("[data-master-preview-title]");
    const downloadLink = modal.querySelector("[data-master-preview-download]");
    const downloadLabel = modal.querySelector("[data-master-preview-download-label]");
    const qrDownloadLink = modal.querySelector("[data-master-preview-qr-download]");
    const labelQr = modal.querySelector("[data-master-label-qr]");
    const labelQrEmpty = modal.querySelector("[data-master-label-qr-empty]");

    function textValue(value) {
        const text = (value || "").trim();
        return text || "-";
    }

    function setText(selector, value) {
        const element = modal.querySelector(selector);
        if (element) {
            element.textContent = textValue(value);
        }
    }

    function setImage(image, src, alt) {
        if (!image) {
            return;
        }

        if (!src) {
            image.removeAttribute("src");
            image.setAttribute("alt", "");
            image.hidden = true;
            return;
        }

        image.src = src;
        image.alt = alt || "";
        image.hidden = false;
    }

    function setDownload(button) {
        if (!downloadLink || !downloadLabel) {
            return;
        }

        const href = button.getAttribute("data-preview-download") || "#";
        downloadLink.href = href;
        downloadLink.toggleAttribute("download", href !== "#");
        downloadLabel.textContent = "Download Label";
    }

    function setQrDownload(button) {
        if (!qrDownloadLink) {
            return;
        }

        const href = button.getAttribute("data-label-qr") || "#";
        qrDownloadLink.href = href;
        qrDownloadLink.toggleAttribute("download", href !== "#");
        qrDownloadLink.hidden = href === "#";
    }

    function openModal(button) {
        const previewTitle = button.getAttribute("data-preview-title") || "Preview";

        if (title) {
            title.textContent = previewTitle;
        }

        setDownload(button);
        setQrDownload(button);
        setText("[data-master-label-name]", button.getAttribute("data-label-name"));
        setText("[data-master-label-type]", button.getAttribute("data-label-type"));
        setText("[data-master-label-bmn]", button.getAttribute("data-label-bmn"));
        setText("[data-master-label-lab]", button.getAttribute("data-label-lab"));

        const qrSrc = button.getAttribute("data-label-qr") || "";
        setImage(labelQr, qrSrc, "QR Code " + textValue(button.getAttribute("data-label-name")));
        if (labelQrEmpty) {
            labelQrEmpty.hidden = Boolean(qrSrc);
        }

        modal.classList.add("show");
        document.body.classList.add("is-scroll-locked");
    }

    function closeModal() {
        modal.classList.remove("show");
        document.body.classList.remove("is-scroll-locked");
    }

    openButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            openModal(button);
        });
    });

    modal.querySelectorAll("[data-master-preview-close]").forEach(function (element) {
        element.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("show")) {
            closeModal();
        }
    });
})();

(function () {
    const modal = document.querySelector("[data-bulk-label-modal]");
    const openButton = document.querySelector("[data-bulk-label-open]");

    if (!modal || !openButton) {
        return;
    }

    const itemChecks = Array.from(modal.querySelectorAll("[data-bulk-label-item]"));
    const checkAll = modal.querySelector("[data-bulk-label-check-all]");
    const form = modal.querySelector("[data-bulk-label-form]");

    function openModal() {
        modal.classList.add("show");
        document.body.classList.add("is-scroll-locked");
    }

    function closeModal() {
        modal.classList.remove("show");
        document.body.classList.remove("is-scroll-locked");
    }

    function syncCheckAll() {
        if (!checkAll || !itemChecks.length) {
            return;
        }

        const checkedCount = itemChecks.filter((checkbox) => checkbox.checked).length;
        checkAll.checked = checkedCount === itemChecks.length;
        checkAll.indeterminate = checkedCount > 0 && checkedCount < itemChecks.length;
    }

    openButton.addEventListener("click", openModal);

    modal.querySelectorAll("[data-bulk-label-close]").forEach(function (element) {
        element.addEventListener("click", closeModal);
    });

    if (checkAll) {
        checkAll.addEventListener("change", function () {
            itemChecks.forEach(function (checkbox) {
                checkbox.checked = checkAll.checked;
            });
            syncCheckAll();
        });
    }

    itemChecks.forEach(function (checkbox) {
        checkbox.addEventListener("change", syncCheckAll);
    });

    if (form) {
        form.addEventListener("submit", function (event) {
            const hasSelected = itemChecks.some((checkbox) => checkbox.checked);
            if (!hasSelected) {
                event.preventDefault();
                window.alert("Pilih minimal satu label barang.");
            }
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("show")) {
            closeModal();
        }
    });
})();
