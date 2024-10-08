import os
from PIL import Image
from pathlib import Path

from oot_diffusion.inference_segmentation import ClothesMaskModel
from .inference_ootd import OOTDiffusion
from .ootd_utils import resize_crop_center,read_image_from_url_and_convert


DEFAULT_HG_ROOT = Path(os.getcwd()) / "oodt_models"


class OOTDiffusionModel:
    def __init__(self, hg_root: str = None, cache_dir: str = None, model_type: str = "dc", category: str = "upperbody"):
        """
        Args:
            hg_root (str, optional): Path to the hg root directory. Defaults to CWD.
            cache_dir (str, optional): Path to the cache directory. Defaults to None.
        """
        if hg_root is None:
            hg_root = DEFAULT_HG_ROOT
        self.hg_root = hg_root
        self.cache_dir = cache_dir
        self.model_type = model_type
        self.category = category

    def load_pipe(self):
        self.pipe = OOTDiffusion(
            hg_root=self.hg_root,
            cache_dir=self.cache_dir,
            model_type=self.model_type
        )
        self.cmm = ClothesMaskModel(hg_root=self.hg_root, cache_dir=self.cache_dir, category=self.category)
        return self.pipe

    def get_pipe(self):
        if not hasattr(self, "pipe"):
            self.load_pipe()
        return self.pipe

    def generate(
        self,
        cloth_path: str | bytes | Path | Image.Image,
        model_path: str | bytes | Path | Image.Image,
        seed: int = 0,
        steps: int = 10,
        cfg: float = 2.0,
        num_samples: int = 1
    ):
        return self.generate_static(
            self.get_pipe(),
            self.cmm,
            cloth_path,
            model_path,
            self.hg_root,
            seed,
            steps,
            cfg,
            num_samples,
            self.category
        )

    @staticmethod
    def generate_static(
        pipe: OOTDiffusion,
        cmm: ClothesMaskModel,
        cloth_path: str | bytes | Path | Image.Image,
        model_path: str | bytes | Path | Image.Image,
        hg_root: str = None,
        seed: int = 0,
        steps: int = 10,
        cfg: float = 2.0,
        num_samples: int = 1,
        category: str = None
    ):
        if hg_root is None:
            hg_root = DEFAULT_HG_ROOT

        category = category

        if isinstance(cloth_path, Image.Image):
            cloth_image = cloth_path
        elif isinstance(cloth_path, str) and 'https://' in cloth_path:
            cloth_image = read_image_from_url_and_convert(cloth_path)
        else:
            cloth_image = Image.open(cloth_path)

        if isinstance(model_path, Image.Image):
            model_image = model_path
        elif isinstance(model_path, str) and 'https://' in model_path:
            model_image = read_image_from_url_and_convert(model_path)
        else:
            model_image = Image.open(model_path)
            
        model_image = resize_crop_center(model_image, 768, 1024).convert("RGB")
        cloth_image = resize_crop_center(cloth_image, 768, 1024).convert("RGB")

        (
            masked_vton_img,
            mask,
            _,
            _,
            _,
        ) = cmm.generate(model_image)

        mask = mask.resize((768, 1024), Image.NEAREST)
        masked_vton_img = masked_vton_img.resize((768, 1024), Image.NEAREST)

        images = pipe(
            category=category,
            image_garm=cloth_image,
            image_vton=masked_vton_img,
            mask=mask,
            image_ori=model_image,
            num_samples=num_samples,
            num_steps=steps,
            image_scale=cfg,
            seed=seed,
        )

        masked_vton_img = masked_vton_img.convert("RGB")

        return (images, masked_vton_img)
