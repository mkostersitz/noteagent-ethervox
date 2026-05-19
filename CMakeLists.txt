cmake_minimum_required(VERSION 3.16)
project(noteagent_ethervox VERSION 0.2.0 LANGUAGES C CXX)

# Build the EtherVox C SDK as a shared library for Python ctypes.
# The SDK source lives at vendor/ethervoxai (git submodule).
if(NOT EXISTS "${CMAKE_SOURCE_DIR}/vendor/ethervoxai/CMakeLists.txt")
    message(FATAL_ERROR
        "EtherVox submodule not initialised. Run: git submodule update --init --recursive")
endif()

add_subdirectory(vendor/ethervoxai)
