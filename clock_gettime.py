#!/usr/bin/python

from cffi import FFI

ffi = FFI()
ffi.cdef("""
#define CLOCK_REALTIME ...
#define CLOCK_MONOTONIC ...
#define CLOCK_PROCESS_CPUTIME_ID ...
#define CLOCK_THREAD_CPUTIME_ID ...
#define CLOCK_MONOTONIC_RAW ...
#define CLOCK_REALTIME_COARSE ...
#define CLOCK_MONOTONIC_COARSE ...
#define CLOCK_BOOTTIME ...
typedef int clockid_t;
struct timespec
{
    long tv_sec;            /* Seconds.  */
    long tv_nsec;  /* Nanoseconds.  */
};
int clock_gettime (clockid_t __clock_id, struct timespec *__tp);
""")

ffi_lib = ffi.verify("""
#include <time.h>
""", libraries=['rt'])

def clock_gettime(clock_id):
    ts = ffi.new('struct timespec *')
    if ffi_lib.clock_gettime(clock_id, ts) < 0:
        raise OSError(ffi.errno, 'clock_gettime failed')
    return ts.tv_sec + ts.tv_nsec / 1e9

CLOCK_REALTIME = ffi_lib.CLOCK_REALTIME
CLOCK_MONOTONIC = ffi_lib.CLOCK_MONOTONIC
CLOCK_PROCESS_CPUTIME_ID = ffi_lib.CLOCK_PROCESS_CPUTIME_ID
CLOCK_THREAD_CPUTIME_ID = ffi_lib.CLOCK_THREAD_CPUTIME_ID
CLOCK_MONOTONIC_RAW = ffi_lib.CLOCK_MONOTONIC_RAW
CLOCK_REALTIME_COARSE = ffi_lib.CLOCK_REALTIME_COARSE
CLOCK_MONOTONIC_COARSE = ffi_lib.CLOCK_MONOTONIC_COARSE
CLOCK_BOOTTIME = ffi_lib.CLOCK_BOOTTIME

