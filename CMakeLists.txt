cmake_minimum_required(VERSION 3.16)
project(noteagent_ethervox VERSION 0.2.0 LANGUAGES C CXX)

if(NOT EXISTS "${CMAKE_SOURCE_DIR}/vendor/ethervoxai/CMakeLists.txt")
    message(FATAL_ERROR
        "EtherVox submodule not initialised. Run: git submodule update --init --recursive")
endif()

# Build the SDK static lib first.
add_subdirectory(vendor/ethervoxai)

# Write a tiny shim so CMake has a source file for the SHARED target.
file(WRITE "${CMAKE_BINARY_DIR}/ethervox_shim.c" "/* shim */\n")

# Wrap the static library in a shared library so Python ctypes can load it.
add_library(ethervox SHARED "${CMAKE_BINARY_DIR}/ethervox_shim.c")

target_include_directories(ethervox PUBLIC
    "${CMAKE_SOURCE_DIR}/vendor/ethervoxai/include"
)

# Ensure the static SDK is fully built before we link the shared wrapper.
add_dependencies(ethervox ethervoxai)

# Pull every symbol from the static SDK into the shared lib.
if(APPLE)
    target_link_libraries(ethervox PRIVATE
        -Wl,-force_load,$<TARGET_FILE:ethervoxai>
    )
    # macOS frameworks and system libs the SDK needs
    find_package(CURL REQUIRED)
    target_link_libraries(ethervox PRIVATE CURL::libcurl "-framework CoreAudio" "-framework AudioToolbox")
else()
    target_link_libraries(ethervox PRIVATE
        -Wl,--whole-archive ethervoxai -Wl,--no-whole-archive
    )
endif()

set_target_properties(ethervox PROPERTIES
    OUTPUT_NAME "ethervox"
    PREFIX      "lib"
    SUFFIX      ".dylib"
    MACOSX_RPATH ON
    INSTALL_RPATH "@rpath"
)

install(TARGETS ethervox LIBRARY DESTINATION lib)
