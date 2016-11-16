import django
from django.apps import apps
from imagekit import ImageSpec
from imagekit.cachefiles import ImageCacheFile
import pilkit.processors


class Image:
    def __init__(self, resultrowproxy=None):
        if resultrowproxy:
            self.name = resultrowproxy['image']
            self.mime_type = resultrowproxy['mime_type']


class ImageFactory(object):
    processors = {
        'size': pilkit.processors.SmartResize,
    }

    def get_generator(self, w, h, processor='size'):
        processor = self.processors.get(processor)

        class Generator(ImageSpec):
            processors = [processor(w, h, upscale=True)]
            # format = 'JPEG'
            options = {'quality': 70}

            def get_hash(self):
                return '{}x{}'.format(w, h)

        return Generator

    def get_image(self, image, w, h):
        generator = self.get_generator(w, h)(source=image)
        file = ImageCacheFile(generator)
        file.generate()
        return file

    def resize(self, image_name, w, h):
        django.setup()
        Image = apps.get_model('files.Image')
        image = Image(image=image_name)
        self.get_image(image.image, w, h)
