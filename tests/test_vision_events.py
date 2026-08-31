from ailamp.models import BoundingBox, VisionEventType
from ailamp.services.pose_gesture import PoseKeypoints, classify_pose_gesture
from ailamp.services.vision import classify_person_position
from ailamp.simulation.sim_vision import classify_virtual_target


def test_classifies_camera_person_position():
    frame = (640, 480)

    assert classify_person_position(None, frame).event_type == VisionEventType.NO_PERSON
    assert classify_person_position(BoundingBox(20, 120, 100, 260, 0.8, "person"), frame).event_type == VisionEventType.PERSON_LEFT
    assert classify_person_position(BoundingBox(270, 120, 100, 220, 0.8, "person"), frame).event_type == VisionEventType.PERSON_CENTER
    assert classify_person_position(BoundingBox(520, 120, 100, 220, 0.8, "person"), frame).event_type == VisionEventType.PERSON_RIGHT
    assert classify_person_position(BoundingBox(120, 20, 420, 420, 0.9, "person"), frame).event_type == VisionEventType.PERSON_CLOSE
    assert classify_person_position(BoundingBox(300, 160, 40, 80, 0.7, "person"), frame).event_type == VisionEventType.PERSON_FAR


def test_classifies_virtual_target_events():
    assert classify_virtual_target(None).event_type == VisionEventType.NO_PERSON
    assert classify_virtual_target((-0.6, 0.0, 1.5)).event_type == VisionEventType.PERSON_LEFT
    assert classify_virtual_target((0.0, 0.0, 1.5)).event_type == VisionEventType.PERSON_CENTER
    assert classify_virtual_target((0.6, 0.0, 1.5)).event_type == VisionEventType.PERSON_RIGHT
    assert classify_virtual_target((0.0, 0.0, 0.45)).event_type == VisionEventType.PERSON_CLOSE
    assert classify_virtual_target((0.0, 0.0, 3.8)).event_type == VisionEventType.PERSON_FAR


def test_classifies_camera_person_position_with_custom_thresholds():
    event = classify_person_position(
        BoundingBox(210, 120, 100, 100, 0.8, "person"),
        (640, 480),
        left_threshold=-0.50,
        right_threshold=0.50,
    )

    assert event.event_type == VisionEventType.PERSON_CENTER


def test_classifies_hand_gestures_for_lamp_position():
    frame = (640, 480)

    assert classify_pose_gesture(
        PoseKeypoints.from_named(frame, nose=(320, 150), left_shoulder=(270, 240), right_shoulder=(370, 240), left_wrist=(120, 170))
    ).event_type == VisionEventType.GESTURE_LEFT
    assert classify_pose_gesture(
        PoseKeypoints.from_named(frame, nose=(320, 150), left_shoulder=(270, 240), right_shoulder=(370, 240), right_wrist=(520, 170))
    ).event_type == VisionEventType.GESTURE_RIGHT
    assert classify_pose_gesture(
        PoseKeypoints.from_named(frame, nose=(320, 170), left_shoulder=(270, 260), right_shoulder=(370, 260), right_wrist=(330, 70))
    ).event_type == VisionEventType.GESTURE_UP
    assert classify_pose_gesture(
        PoseKeypoints.from_named(frame, nose=(320, 130), left_shoulder=(270, 210), right_shoulder=(370, 210), right_wrist=(330, 390))
    ).event_type == VisionEventType.GESTURE_DOWN


def test_classifies_study_and_attention_postures():
    frame = (640, 480)

    studying = PoseKeypoints.from_named(
        frame,
        nose=(320, 245),
        left_eye=(300, 210),
        right_eye=(340, 210),
        left_shoulder=(270, 260),
        right_shoulder=(370, 260),
    )
    looking = PoseKeypoints.from_named(
        frame,
        nose=(320, 145),
        left_eye=(300, 135),
        right_eye=(340, 135),
        left_shoulder=(270, 260),
        right_shoulder=(370, 260),
    )

    assert classify_pose_gesture(studying).event_type == VisionEventType.POSTURE_STUDYING
    assert classify_pose_gesture(looking).event_type == VisionEventType.LOOKING_AT_LAMP
