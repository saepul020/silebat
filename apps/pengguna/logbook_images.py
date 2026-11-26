from io import BytesIO
from pathlib import Path

from django import forms
from PIL import Image, ImageOps
from pillow_heif import open_heif

from apps.core.upload_validation import build_max_upload_size_message, validate_uploaded_file

IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'heic', 'heif'}
IMAGE_ERROR = 'Dokumentasi Kegiatan harus berupa gambar JPG, JPEG, PNG, HEIC, atau HEIF yang valid.'


def read_image(file):
    validate_uploaded_file(
        file, allowed_extensions={'.' + ext for ext in IMAGE_EXTENSIONS},
        invalid_extension_message=IMAGE_ERROR,
        max_size_message=build_max_upload_size_message('Dokumentasi Kegiatan'),
    )
    image = None
    try:
        file.seek(0)
        if Path(file.name).suffix.lower() in {'.heic', '.heif'}:
            heif = open_heif(file)
            if heif.size[0] * heif.size[1] > Image.MAX_IMAGE_PIXELS:
                raise ValueError('Gambar terlalu besar.')
            image = heif.to_pillow()
        else:
            image = Image.open(file)
            if image.format not in {'JPEG', 'PNG'}:
                raise ValueError('Format gambar tidak didukung.')
        if image.width * image.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError('Gambar terlalu besar.')
        image.load()
        return image
    except (OSError, ValueError, RuntimeError, Image.DecompressionBombError) as error:
        if image is not None:
            image.close()
        raise forms.ValidationError(IMAGE_ERROR) from error
    finally:
        file.seek(0)


def preview_image(file):
    with read_image(file) as image:
        preview = ImageOps.exif_transpose(image).convert('RGB')
        preview.thumbnail((1600, 1600))
        output = BytesIO()
        preview.save(output, format='JPEG', quality=90)
        preview.close()
        return output.getvalue()
