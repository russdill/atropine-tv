"""
The MIT License (MIT)

Copyright (c) 2014 Stuart Clark

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from ctypes import *
import struct
import socket

_hdhomerun = CDLL("libhdhomerun.so.2")

try:
    # 20160130 changes the type of bool_t which changes the offsets of
    # structure members, detect and account for this by testing for the
    # thread_cond_init symbols which 20160130 also adds.
    _hdhomerun.thread_cond_init
    class _bool_t(c_uint8):
        pass
except:
    class _bool_t(c_int):
        pass

class _hdhomerun_device_selector_t(Structure):
    pass

class _hdhomerun_device_t(Structure):
    pass

class _hdhomerun_channel_entry_t(Structure):
    _fields_ = [("next", c_void_p),
        ("prev", c_void_p),
        ("frequency", c_uint32),
        ("channel_number", c_uint16),
        ("name", c_char * 16)]

class _hdhomerun_channel_list_t(Structure):
    _fields_ = [("head", c_void_p),
        ("tail", c_void_p)]

class _hdhomerun_discover_device_t(Structure):
    _fields_ = [("ip_addr", c_uint32),
        ("device_type", c_uint32),
        ("device_id", c_uint32),
        ("tuner_count", c_uint8),
        ("is_legacy", _bool_t),
        ("device_auth", c_char * 25),
        ("base_url", c_char * 29)]

class _hdhomerun_tuner_status_t(Structure):
    _fields_ = [("channel", c_char * 32),
        ("lock_str", c_char * 32),
        ("signal_present", _bool_t),
        ("lock_supported", _bool_t),
        ("lock_unsupported", _bool_t),
        ("signal_strength", c_uint),
        ("signal_to_noise_quality", c_uint),
        ("symbol_error_quality", c_uint),
        ("raw_bits_per_second", c_uint32),
        ("packets_per_second", c_uint32)]

class _hdhomerun_channelscan_program_t(Structure):
    _fields_ = [("program_str", c_char * 64),
        ("program_number", c_uint16),
        ("virtual_major", c_uint16),
        ("virtual_minor", c_uint16),
        ("type", c_uint16),
        ("name", c_char * 32)]

class _hdhomerun_channelscan_result_t(Structure):
    _fields_ = [("channel_str", c_char * 64),
        ("channelmap", c_uint32),
        ("frequency", c_uint32),
        ("status", _hdhomerun_tuner_status_t),
        ("program_count", c_int),
        ("programs", _hdhomerun_channelscan_program_t * 64),
        ("transport_stream_id_detected", _bool_t),
        ("original_network_id_detected", _bool_t),
        ("transport_stream_id", c_uint16),
        ("original_network_id", c_uint16)]

class _hdhomerun_video_stats_t(Structure):
    _fields_ = [("packet_count", c_uint32),
        ("network_error_count", c_uint32),
        ("transport_error_count", c_uint32),
        ("sequence_error_count", c_uint32),
        ("overflow_error_count", c_uint32)]

class _hdhomerun_tuner_vstatus_t(Structure):
    _fields_ = [("vchannel", c_char * 32),
        ("name", c_char * 32),
        ("auth", c_char * 32),
        ("cci", c_char * 32),
        ("cgms", c_char * 32),
        ("not_subscribed", _bool_t),
        ("not_available", _bool_t),
        ("copy_protected", _bool_t)]


def _ip2num(ip):
    return struct.unpack("!I", socket.inet_aton(ip))[0]

def _num2ip(num):
    return socket.inet_ntoa(struct.pack("!L", num))

class HDHomerunDeviceSelector(object):
    _fn_create                     = _hdhomerun.hdhomerun_device_selector_create
    _fn_destroy                    = _hdhomerun.hdhomerun_device_selector_destroy
    _fn_get_device_count           = _hdhomerun.hdhomerun_device_selector_get_device_count
    _fn_load_from_str              = _hdhomerun.hdhomerun_device_selector_load_from_str
    _fn_load_from_file             = _hdhomerun.hdhomerun_device_selector_load_from_file
    #_fn_load_from_windows_registry = _hdhomerun.hdhomerun_device_selector_load_from_windows_registry
    _fn_add_device                 = _hdhomerun.hdhomerun_device_selector_add_device
    _fn_remove_device              = _hdhomerun.hdhomerun_device_selector_remove_device
    _fn_find_device                = _hdhomerun.hdhomerun_device_selector_find_device
    _fn_choose_and_lock            = _hdhomerun.hdhomerun_device_selector_choose_and_lock

    _fn_create.restype                     = POINTER(_hdhomerun_device_selector_t)
    _fn_get_device_count.restype           = c_int32
    _fn_load_from_str.restype              = c_int32
    _fn_load_from_file.restype             = c_int32
    #_fn_load_from_windows_registry.restype = c_int32
    _fn_find_device.restype                = POINTER(_hdhomerun_device_t)
    _fn_choose_and_lock.restype            = POINTER(_hdhomerun_device_t)

    def __init__(self, debug=None, *args, **kwargs):
        #super(HDHomerunDeviceSelector, self).__init__(*args, **kwargs)
        self.ptr = HDHomerunDeviceSelector._fn_create(debug)
        self._devices = list()

        if not self.ptr:
            raise RuntimeError("Error creating device")

    def __del__(self):
        HDHomerunDeviceSelector._fn_destroy(self.ptr, c_bool(False))

    def __len__(self):
        return len(self._devices)

    def __getitem__(self, key):
        return self._devices[key]

    def __setitem__(self, key, value):
        if key >= len(self._devices):
            raise IndexError('Index beyond list')
        HDHomerunDeviceSelector._fn_remove_device(self.ptr, self._devices[key].ptr)
        if value in self._devices and self._devices.index(value) != key:
            raise Exception('Already contains item')
        self._devices[key] = value
        HDHomerunDeviceSelector._fn_add_device(self.ptr, value.ptr)

    def __delitem__(self, key):
        if key >= len(self._devices):
            raise IndexError('Index beyond list')
        HDHomerunDeviceSelector._fn_remove_device(self.ptr, self._devices[key].ptr)
        del self._devices[key]

    def __iter__(self):
        return self._devices.__iter__()

    def __contains__(self, item):
        return item in self._devices

    def append(self, item):
        HDHomerunDeviceSelector._fn_add_device(self.ptr, item.ptr)
        if item not in self._devices:
            self._devices.append(item)

    def count(self):
        return self._devices.count()

    def index(self, item):
        return self._devices.index(item)

    def extend(self, items):
        for item in items:
            self.append(item)

    def remove(self, item):
        self._devices.remove(item)
        HDHomerunDeviceSelector._fn_remove_device(self.ptr, item.ptr)

    def load_from_str(self, strname):
        ret = HDHomerunDeviceSelector._fn_load_from_str(self.ptr, create_string_buffer(strname))

        if ret < 0:
            raise RuntimeError("Error loading device selector from str")

        self._sync()

    def load_from_file(self, filename):
        ret = HDHomerunDeviceSelector._fn_load_from_file(self.ptr, create_string_buffer(filename))

        if ret < 0:
            raise RuntimeError("Error loading device selector from file")

        self._sync()

    """
    def load_from_windows_registery(self, wsource):
        ret = HDHomerunDeviceSelector._fn_load_from_windows_registery(self.ptr, create_unicode_buffer(wsource))

        if ret < 0:
            raise RuntimeError("Error loading device selector from registery")

        self._sync()
    """

    def _sync(self):
        arry = (c_void_p*self._fn_get_device_count(self.ptr))()
        for i in range(0, self._fn_get_device_count(self.ptr)):
            if not [x for x in self._devices if arry[i] == addressof(x.ptr.contents)]:
                self._devices.append(HDHomerunDevice(arry[i]))

    def find_device(self, device_id, tuner_index):
        ret = HDHomerunDeviceSelector._fn_find_device(self.ptr, c_uint32(device_id), c_uint(tuner_index))
        if not ret:
            raise KeyError('device_id=%d, tuner_index=%d not found' % (device_id, tuner_index))
        for dev in self._devices:
            if addressof(ret.contents) == addressof(dev.ptr.contents):
                return dev
        raise Exception('Inconsistent state')

    def choose_and_lock(self, preferred=None):
        ptr = preferred.ptr if preferred else None
        ret = HDHomerunDeviceSelector._fn_choose_and_lock(self.ptr, ptr)
        for dev in self._devices:
            if not dev.ptr:
                continue
            if addressof(ret.contents) == addressof(dev.ptr.contents):
                return dev
        return None


class HDHomerunDevice(object):
    type_wildcard = 0xFFFFFFFF
    type_tuner    = 0x00000001
    id_wildcard   = 0xFFFFFFFF

    _colour_neutral = 0xFFFFFFFF
    _colour_red     = 0xFFFF0000
    _colour_yellow  = 0xFFFFFF00
    _colour_green   = 0xFF00C000

    _program_normal  = 0
    _program_nodata  = 1
    _program_control = 2
    _program_encrypt = 3

    _fn_find           = _hdhomerun.hdhomerun_discover_find_devices_custom_v2
    _fn_validate       = _hdhomerun.hdhomerun_discover_validate_device_id

    _fn_create         = _hdhomerun.hdhomerun_device_create
    _fn_create_str     = _hdhomerun.hdhomerun_device_create_from_str
    _fn_destroy        = _hdhomerun.hdhomerun_device_destroy

    _fn_name           = _hdhomerun.hdhomerun_device_get_name
    _fn_id_get         = _hdhomerun.hdhomerun_device_get_device_id
    _fn_ip_get         = _hdhomerun.hdhomerun_device_get_device_ip
    _fn_req_id_get     = _hdhomerun.hdhomerun_device_get_device_id_requested
    _fn_req_ip_get     = _hdhomerun.hdhomerun_device_get_device_ip_requested
    _fn_tuner_get      = _hdhomerun.hdhomerun_device_get_tuner
    _fn_change_device  = _hdhomerun.hdhomerun_device_set_device
    _fn_tuner_set      = _hdhomerun.hdhomerun_device_set_tuner

    _fn_local_ip_get   = _hdhomerun.hdhomerun_device_get_local_machine_addr

    _fn_tstatus        = _hdhomerun.hdhomerun_device_get_tuner_status
    _fn_vstatus_get    = _hdhomerun.hdhomerun_device_get_tuner_vstatus
    _fn_streaminfo_get = _hdhomerun.hdhomerun_device_get_tuner_streaminfo
    _fn_channel_get    = _hdhomerun.hdhomerun_device_get_tuner_channel
    _fn_vchannel_get   = _hdhomerun.hdhomerun_device_get_tuner_vchannel
    _fn_channelmap_get = _hdhomerun.hdhomerun_device_get_tuner_channelmap
    _fn_filter_get     = _hdhomerun.hdhomerun_device_get_tuner_filter
    _fn_program_get    = _hdhomerun.hdhomerun_device_get_tuner_program
    _fn_target_get     = _hdhomerun.hdhomerun_device_get_tuner_target
    _fn_lockkey_get    = _hdhomerun.hdhomerun_device_get_tuner_lockkey_owner
    _fn_ir_target_get  = _hdhomerun.hdhomerun_device_get_ir_target
    _fn_version        = _hdhomerun.hdhomerun_device_get_version
    _fn_supported_get  = _hdhomerun.hdhomerun_device_get_supported
    _fn_tstatus_ssc    = _hdhomerun.hdhomerun_device_get_tuner_status_ss_color
    _fn_tstatus_snqc   = _hdhomerun.hdhomerun_device_get_tuner_status_snq_color
    _fn_tstatus_seqc   = _hdhomerun.hdhomerun_device_get_tuner_status_seq_color
    _fn_model          = _hdhomerun.hdhomerun_device_get_model_str

    _fn_channel_set    = _hdhomerun.hdhomerun_device_set_tuner_channel
    _fn_vchannel_set   = _hdhomerun.hdhomerun_device_set_tuner_vchannel
    _fn_channelmap_set = _hdhomerun.hdhomerun_device_set_tuner_channelmap
    _fn_program_set    = _hdhomerun.hdhomerun_device_set_tuner_program
    _fn_target_set     = _hdhomerun.hdhomerun_device_set_tuner_target
    _fn_ir_target_set  = _hdhomerun.hdhomerun_device_set_ir_target
    _fn_ir_mod_set     = _hdhomerun.hdhomerun_device_set_sys_dvbc_modulation

    _fn_get            = _hdhomerun.hdhomerun_device_get_var
    _fn_set            = _hdhomerun.hdhomerun_device_set_var

    _fn_lock           = _hdhomerun.hdhomerun_device_tuner_lockkey_request
    _fn_unlock         = _hdhomerun.hdhomerun_device_tuner_lockkey_release
    _fn_force          = _hdhomerun.hdhomerun_device_tuner_lockkey_force
    _fn_lockkey_set    = _hdhomerun.hdhomerun_device_tuner_lockkey_use_value

    _fn_wlock          = _hdhomerun.hdhomerun_device_wait_for_lock

    _fn_video_start    = _hdhomerun.hdhomerun_device_stream_start
    _fn_video_recv     = _hdhomerun.hdhomerun_device_stream_recv
    _fn_video_flush    = _hdhomerun.hdhomerun_device_stream_flush
    _fn_video_stop     = _hdhomerun.hdhomerun_device_stream_stop

    _fn_scan_start     = _hdhomerun.hdhomerun_device_channelscan_init
    _fn_scan_advance   = _hdhomerun.hdhomerun_device_channelscan_advance
    _fn_scan_detect    = _hdhomerun.hdhomerun_device_channelscan_detect
    _fn_scan_progress  = _hdhomerun.hdhomerun_device_channelscan_get_progress

    _fn_video_stats    = _hdhomerun.hdhomerun_device_get_video_stats

    _fn_create.restype        = POINTER(_hdhomerun_device_t)
    _fn_model.restype         = c_char_p
    _fn_name.restype          = c_char_p
    _fn_id_get.restype        = c_uint32
    _fn_ip_get.restype        = c_uint32
    _fn_tuner_get.restype     = c_uint
    _fn_req_id_get.restype    = c_uint32
    _fn_req_ip_get.restype    = c_uint32
    _fn_local_ip_get.restype  = c_uint32
    _fn_video_recv.restype    = POINTER(c_uint8)
    _fn_scan_progress.restype = c_uint8

    def __init__(self, string=None, ip=None, id=None, tuner=0, debug=None, ptr=None, *args, **kwargs):
        #super(HDHomerunDevice, self).__init__(*args, **kwargs)
        self.ptr = None
        if ptr:
            self.ptr = ptr
        elif string:
            self.ptr = HDHomerunDevice._fn_create_str(c_char_p(string), debug)
        else:
            if ip == None:
                ipnum = 0
            else:
                ipnum = _ip2num(ip)

            if id == None:
                id = self.type_wildcard

            self.ptr = HDHomerunDevice._fn_create(id, ipnum, tuner, debug)

        if not self.ptr:
            raise RuntimeError("Error creating device")

    def __del__(self):
        HDHomerunDevice._fn_destroy(self.ptr)

    def change(self, id, ip):
        ret = HDHomerunDevice._fn_change_device(self.ptr, id, _ip2num(ip))

        if ret < 0:
            raise RuntimeError("Error changing device")

    @property
    def model(self):
        return HDHomerunDevice._fn_model(self.ptr)

    @property
    def name(self):
        return HDHomerunDevice._fn_name(self.ptr)

    def get(self, name):
        buffer = c_char_p()
        error = c_char_p()

        ret = HDHomerunDevice._fn_get(self.ptr, create_string_buffer(name), byref(buffer), byref(error))

        if ret < 0:
            raise RuntimeError("Communication error")

        if ret == 0:
            raise RuntimeError(error.value)

        return buffer.value

    def set(self, name, value):
        pvalue = c_char_p()
        error = c_char_p()

        ret = HDHomerunDevice._fn_set(self.ptr, create_string_buffer(name), create_string_buffer(value), byref(pvalue), byref(error))

        if ret < 0:
            raise RuntimeError("Communication error")

        if ret == 0:
            raise RuntimeError(error.value)

    @property
    def id(self):
        return HDHomerunDevice._fn_id_get(self.ptr)

    @property
    def ip(self):
        return _num2ip(HDHomerunDevice._fn_ip_get(self.ptr))

    @property
    def tuner(self):
        return HDHomerunDevice._fn_tuner_get(self.ptr)

    @tuner.setter
    def tuner(self, value):
        ret = HDHomerunDevice._fn_tuner_set(self.ptr, value)

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def req_id(self):
        return HDHomerunDevice._fn_req_id_get(self.ptr)

    @property
    def req_ip(self):
        return _num2ip(HDHomerunDevice._fn_req_ip_get(self.ptr))

    @property
    def local_ip(self):
        return _num2ip(HDHomerunDevice._fn_local_ip_get(self.ptr))

    @property
    def version(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_version(self.ptr, byref(buffer), None)

        if ret < 0:
            raise RuntimeError("Communication error")

        if ret == 0:
            raise RuntimeError("Firmware error")

        return buffer.value

    @property
    def status(self):
        status = _hdhomerun_tuner_status_t()

        ret = HDHomerunDevice._fn_tstatus(self.ptr, None, byref(status))

        if ret < 0:
            raise RuntimeError("Communication error")

        return self._decode_status(status)

    def _decode_status(self, status):
        data = {}

        data['channel']    = status.channel
        data['ss']         = status.signal_strength
        data['snq']        = status.signal_to_noise_quality
        data['seq']        = status.symbol_error_quality
        data['bps']        = status.raw_bits_per_second
        data['pps']        = status.packets_per_second
        data['signal']     = status.signal_present
        data['lock_type']  = status.lock_str
        data['ss_colour']  = self._status_colour("ss", status)
        data['snq_colour'] = self._status_colour("snq", status)
        data['seq_colour'] = self._status_colour("seq", status)

        if status.lock_supported:
            data['locked'] = True
        else:
            data['locked'] = status.lock_unsupported

        return data

    def _status_colour(self, type, status):
        if type == "seq":
            colour = HDHomerunDevice._fn_tstatus_seqc(byref(status))
        elif type == "snq":
            colour = HDHomerunDevice._fn_tstatus_snqc(byref(status))
        elif type == "ss":
            colour = HDHomerunDevice._fn_tstatus_ssc(byref(status))
        else:
            raise RuntimeError("Unknown type")

        if colour == HDHomerunDevice._colour_neutral:
            return 'neutral'
        elif colour == HDHomerunDevice._colour_red:
            return 'red'
        elif colour == HDHomerunDevice._colour_yellow:
            return 'yellow'
        elif colour == HDHomerunDevice._colour_green:
            return 'green'

        return 'unknown'

    def video_start(self):
        ret = HDHomerunDevice._fn_video_start(self.ptr)

        if ret < 0:
            raise RuntimeError("Communication error")

    def video_stop(self):
        HDHomerunDevice._fn_video_stop(self.ptr)

    def video_flush(self):
        HDHomerunDevice._fn_video_flush(self.ptr)

    def video_receive(self, buffer_size=(20000000 / 8)):
        size = c_size_t()

        ptr = HDHomerunDevice._fn_video_recv(self.ptr, c_size_t(buffer_size), byref(size))

        if size.value == 0:
            return

        data = cast(ptr, POINTER(c_uint8 * size.value))

        d_array = data.contents[:size.value]

        return bytearray(d_array)

    @property
    def video_stats(self):
        buffer = _hdhomerun_video_stats_t()

        HDHomerunDevice._fn_video_stats(self.ptr, byref(buffer))

        data = {}

        data['packets']   = buffer.packet_count
        data['network']   = buffer.network_error_count
        data['transport'] = buffer.transport_error_count
        data['sequence']  = buffer.sequence_error_count
        data['overflow']  = buffer.overflow_error_count

        return data

    @property
    def target(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_target_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @target.setter
    def target(self, value):
        ret = HDHomerunDevice._fn_target_set(self.ptr, create_string_buffer(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def channelmap(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_channelmap_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @channelmap.setter
    def channelmap(self, value):
        ret = HDHomerunDevice._fn_channelmap_set(self.ptr, c_char_p(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def channel(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_channel_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @channel.setter
    def channel(self, value):
        ret = HDHomerunDevice._fn_channel_set(self.ptr, create_string_buffer(value))

        if ret < 0:
            raise RuntimeError("Communication error")

        status = _hdhomerun_tuner_status_t()

        ret = HDHomerunDevice._fn_wlock(self.ptr, byref(status))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def streaminfo(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_streaminfo_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @property
    def program(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_program_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @program.setter
    def program(self, value):
        ret = HDHomerunDevice._fn_program_set(self.ptr, create_string_buffer(str(value)))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def features(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_supported_get(self.ptr, None, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @property
    def vchannel(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_vchannel_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @vchannel.setter
    def vchannel(self, value):
        ret = HDHomerunDevice._fn_vchannel_set(self.ptr, c_char_p(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def filter(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_filter_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @filter.setter
    def filter(self, value):
        ret = HDHomerunDevice._fn_filter_set(self.ptr, c_char_p(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def ir_target(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_ir_target_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @ir_target.setter
    def ir_target(self, value):
        ret = HDHomerunDevice._fn_ir_target_set(self.ptr, c_char_p(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    def scan_start(self, channelmap=None):
        if not channelmap:
            channelmap = self.channelmap

        ret = HDHomerunDevice._fn_scan_start(self.ptr, c_char_p(channelmap))

        if ret < 0:
            raise RuntimeError("")

    @property
    def scan_progress(self):
        return HDHomerunDevice._fn_scan_progress(self.ptr)

    def scan_get(self):
        buffer = _hdhomerun_channelscan_result_t()

        ret = HDHomerunDevice._fn_scan_advance(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("")

        if ret == 0:
            return None

        ret = HDHomerunDevice._fn_scan_detect(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("")

        data = {}

        (channelmap, channel) = buffer.channel_str.split(":")

        data['channel']     = channel
        data['channelmap']  = channelmap
        data['frequency']   = buffer.frequency
        data['status']      = self._decode_status(buffer.status)
        data['ts_detected'] = buffer.transport_stream_id_detected
        data['ts_id']       = buffer.transport_stream_id
        data['programs']    = []

        for i in range(0, buffer.program_count):
            program = {}

            program['number'] = buffer.programs[i].program_number
            program['major']  = buffer.programs[i].virtual_major
            program['minor']  = buffer.programs[i].virtual_minor
            program['name']   = buffer.programs[i].name

            if buffer.programs[i].type == self._program_normal:
                program['type'] = 'normal'
            elif buffer.programs[i].type == self._program_nodata:
                program['type'] = 'no data'
            elif buffer.programs[i].type == self._program_control:
                program['type'] = 'control'
            elif buffer.programs[i].type == self._program_encrypt:
                program['type'] = 'encrypted'
            else:
                program['type'] = 'unknown'

            data['programs'].append(program)

        return data

    def modulation(self, value):
        ret = HDHomerunDevice._fn_ir_mod_set(self.ptr, c_char_p(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    @property
    def vstatus(self):
        buffer = _hdhomerun_tuner_vstatus_t()

        ret = HDHomerunDevice._fn_vstatus_get(self.ptr, None, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        data = {}

        data['vchannel']       = buffer.vchannel
        data['name']           = buffer.name
        data['auth']           = buffer.auth
        data['cci']            = buffer.cci
        data['cgms']           = buffer.cgms
        data['not_subscribed'] = buffer.not_subscribed
        data['not_available']  = buffer.not_available
        data['copy_protected'] = buffer.copy_protected

        return data

    @property
    def lockkey(self):
        buffer = c_char_p()

        ret = HDHomerunDevice._fn_lockkey_get(self.ptr, byref(buffer))

        if ret < 0:
            raise RuntimeError("Communication error")

        return buffer.value

    @lockkey.setter
    def lockkey(self, value):
        ret = HDHomerunDevice._fn_lockkey_set(self.ptr, c_char_p(value))

        if ret < 0:
            raise RuntimeError("Communication error")

    def lock(self):
        ret = HDHomerunDevice._fn_lock(self.ptr)

        if ret < 0:
            raise RuntimeError("")

    def unlock(self, force=False):
        if force:
            ret = HDHomerunDevice._fn_unlock(self.ptr)
        else:
            ret = HDHomerunDevice._fn_force(self.ptr)

        if ret < 0:
            raise RuntimeError("Communication error")

    @staticmethod
    def find_devices(ip=None, devtype=None, id=None, max=64, debug=None):
        if ip == None:
            ip = 0
        else:
            ip = _ip2num(ip)

        if devtype == None:
            devtype = HDHomerunDevice.type_wildcard

        if id == None:
            id = HDHomerunDevice.id_wildcard

        buffer = (_hdhomerun_discover_device_t * max)()

        found = HDHomerunDevice._fn_find(ip, devtype, id, byref(buffer), max)

        if found < 0:
            raise RuntimeError("Discovery error")

        devices = []

        if found > 0:
            for i in range(0, found):
                ip   = _num2ip(buffer[i].ip_addr)
                devtype = buffer[i].device_type
                id   = buffer[i].device_id

                for tuner in range(0, buffer[i].tuner_count):
                    device = HDHomerunDevice(ip=ip, devtype=devtype, id=id,
                        tuner=tuner, debug=debug)
                    devices.append(device)

        return devices

    @staticmethod
    def validate_id(id):
        return HDHomerunDevice._fn_validate(id)
