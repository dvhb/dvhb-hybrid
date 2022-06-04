import django
import pilkit.processors
from django.apps import apps
from imagekit import ImageSpec
from imagekit.cachefiles import ImageCacheFile


class Image:
    def __init__(self, resultrowproxy=None):
        if resultrowproxy:
            self.name = resultrowproxy['image']
            self.mime_type = resultrowproxy['mime_type']


class ImageFactory(object):
    processors = {
        'size': pilkit.processors.SmartResize,
        'width': pilkit.processors.ResizeToCover,
        'height': pilkit.processors.ResizeToCover,
    }

    def get_generator(self, w, h, processor='size'):
        processor = self.processors.get(processor)

        class Generator(ImageSpec):
            processors = [processor(w, h, upscale=True)]
            # format = 'JPEG'
            options = {'quality': 70}

            def get_hash(self):
                return '{}x{}'.format(w if w else '-', h if h else '-')

        return Generator

    def _get_image(self, image, w, h, processor):
        generator = self.get_generator(w, h, processor=processor)(source=image)
        file = ImageCacheFile(generator)
        file.generate()
        return file

    def resize(self, image_name, w, h, processor='size'):
        django.setup()
        Image = apps.get_model('files.Image')
        image = Image(image=image_name)
        self._get_image(image.image, w, h, processor=processor)
