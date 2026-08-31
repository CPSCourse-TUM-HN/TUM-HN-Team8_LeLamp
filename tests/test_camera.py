from ailamp.services.camera import CameraService


def test_camera_service_stores_device_path_and_pixel_format():
    camera = CameraService("/dev/video2", 1280, 720, 30, "YUYV")

    assert camera.device == "/dev/video2"
    assert camera.pixel_format == "YUYV"
