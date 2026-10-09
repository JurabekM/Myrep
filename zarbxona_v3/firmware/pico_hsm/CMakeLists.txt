# Zarbxona Pico HSM — Raspberry Pi Pico (RP2040) ichki dasturi.
#
#   Pico uchun:  cmake -B build -DPICO_SDK_PATH=/yo'l/pico-sdk && cmake --build build
#                → build/zarbxona_pico_hsm.uf2
#   Kompyuterda test uchun (SDK kerak emas):
#                cmake -B build-host -DAQ_HOST=ON && cmake --build build-host
#                → build-host/pico_hsm_host (stdin/stdout orqali gaplashadi)
#
# ML-DSA-65: mldsa-native v2.0.0 (Apache-2.0 / ISC / MIT), aniq commit bilan yuklanadi.
# Internetsiz yig'ish uchun: -DMLDSA_NATIVE_PATH=/yo'l/mldsa-native
cmake_minimum_required(VERSION 3.18)

option(AQ_HOST "Kompyuter uchun (test) yig'ish" OFF)

if(NOT AQ_HOST)
    set(PICO_BOARD pico CACHE STRING "Plata turi")
    include(pico_sdk_import.cmake)
endif()

project(zarbxona_pico_hsm C CXX ASM)
set(CMAKE_C_STANDARD 11)

if(MLDSA_NATIVE_PATH)
    set(mldsa_SOURCE_DIR ${MLDSA_NATIVE_PATH})
else()
    include(FetchContent)
    # SOURCE_SUBDIR — mavjud bo'lmagan papka: faqat yuklanadi, mldsa-native'ning o'z
    # CMake loyihasi (testlari bilan) qo'shilmaydi.
    FetchContent_Declare(mldsa
        GIT_REPOSITORY https://github.com/pq-code-package/mldsa-native.git
        GIT_TAG 834a90d5e846ffa1e1611bd24e160bb2e9b86d35   # v2.0.0
        SOURCE_SUBDIR faqat-manba)
    FetchContent_MakeAvailable(mldsa)
endif()

set(AQ_MANBALAR
    src/aq_hsm.c
    src/aq_keccak.c
    src/aq_arena.c
    src/aq_mldsa.c)
set(AQ_TAKRIF MLD_CONFIG_FILE="aq_mldsa_config.h")
set(AQ_YOLLAR ${CMAKE_CURRENT_SOURCE_DIR}/src ${mldsa_SOURCE_DIR}/mldsa)

if(AQ_HOST)
    add_executable(pico_hsm_host ${AQ_MANBALAR} src/main_host.c)
    target_include_directories(pico_hsm_host PRIVATE ${AQ_YOLLAR})
    target_compile_definitions(pico_hsm_host PRIVATE ${AQ_TAKRIF})
    target_compile_options(pico_hsm_host PRIVATE -O2 -Wall -Wextra)
    find_package(Threads REQUIRED)
    target_link_libraries(pico_hsm_host PRIVATE Threads::Threads)
else()
    pico_sdk_init()
    add_executable(zarbxona_pico_hsm ${AQ_MANBALAR} src/main_pico.c)
    target_include_directories(zarbxona_pico_hsm PRIVATE ${AQ_YOLLAR})
    target_compile_definitions(zarbxona_pico_hsm PRIVATE ${AQ_TAKRIF}
        USBD_PRODUCT="AETHER-Q Pico HSM"
        USBD_MANUFACTURER="AETHER-Q Zarbxona"
        PICO_STDIO_DEFAULT_CRLF=0)
    target_compile_options(zarbxona_pico_hsm PRIVATE -O2 -Wall -fstack-usage)
    target_link_libraries(zarbxona_pico_hsm
        pico_stdlib pico_rand pico_unique_id pico_flash hardware_flash)
    pico_enable_stdio_usb(zarbxona_pico_hsm 1)
    pico_enable_stdio_uart(zarbxona_pico_hsm 0)
    pico_set_program_name(zarbxona_pico_hsm "Zarbxona Pico HSM")
    pico_add_extra_outputs(zarbxona_pico_hsm)
endif()
