#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "HymnPlayer.h"

namespace py = pybind11;

// Wrapper function to handle numpy arrays seamlessly
py::array_t<float> renderAudioWrapper(HymnPlayer& player, int numFrames) {
    // We expect stereo interleaved, so 2 channels
    auto result = py::array_t<float>(numFrames * 2);

    // Get mutable pointer to the data
    py::buffer_info buf = result.request();
    float* ptr = static_cast<float*>(buf.ptr);

    // Call the original renderAudio function
    player.renderAudio(ptr, numFrames);

    return result;
}

PYBIND11_MODULE(hymn_player_ext, m) {
    m.doc() = "Python bindings for the native HymnPlayer C++ audio engine using FluidSynth";

    py::class_<HymnPlayer>(m, "HymnPlayer")
        .def(py::init<const std::string&>(), py::arg("soundfontPath") = "/usr/share/sounds/sf2/FluidR3_GM.sf2")
        .def("load", &HymnPlayer::load, "Load a MIDI file into the player", py::arg("filename"))
        .def("play", &HymnPlayer::play, "Start playback of the loaded MIDI file")
        .def("pause", &HymnPlayer::pause, "Pause playback")
        .def("stop", &HymnPlayer::stop, "Stop playback")
        .def("is_playing", &HymnPlayer::isPlaying, "Check if the player is currently playing")
        .def("render_audio", &renderAudioWrapper, "Render audio into a numpy array of floats (stereo interleaved)", py::arg("numFrames"));
}
