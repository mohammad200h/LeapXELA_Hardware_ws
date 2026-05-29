# generated from rosidl_generator_py/resource/_idl.py.em
# with input from xela_point_cloud_representation:msg/Texel.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_Texel(type):
    """Metaclass of message 'Texel'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('xela_point_cloud_representation')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'xela_point_cloud_representation.msg.Texel')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__texel
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__texel
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__texel
            cls._TYPE_SUPPORT = module.type_support_msg__msg__texel
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__texel

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class Texel(metaclass=Metaclass_Texel):
    """Message class 'Texel'."""

    __slots__ = [
        '_taxel_id',
        '_sensor_name',
        '_x',
        '_y',
        '_z',
        '_joint_x',
        '_joint_y',
        '_joint_z',
    ]

    _fields_and_field_types = {
        'taxel_id': 'int32',
        'sensor_name': 'string',
        'x': 'float',
        'y': 'float',
        'z': 'float',
        'joint_x': 'string',
        'joint_y': 'string',
        'joint_z': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.taxel_id = kwargs.get('taxel_id', int())
        self.sensor_name = kwargs.get('sensor_name', str())
        self.x = kwargs.get('x', float())
        self.y = kwargs.get('y', float())
        self.z = kwargs.get('z', float())
        self.joint_x = kwargs.get('joint_x', str())
        self.joint_y = kwargs.get('joint_y', str())
        self.joint_z = kwargs.get('joint_z', str())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.taxel_id != other.taxel_id:
            return False
        if self.sensor_name != other.sensor_name:
            return False
        if self.x != other.x:
            return False
        if self.y != other.y:
            return False
        if self.z != other.z:
            return False
        if self.joint_x != other.joint_x:
            return False
        if self.joint_y != other.joint_y:
            return False
        if self.joint_z != other.joint_z:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def taxel_id(self):
        """Message field 'taxel_id'."""
        return self._taxel_id

    @taxel_id.setter
    def taxel_id(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'taxel_id' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'taxel_id' field must be an integer in [-2147483648, 2147483647]"
        self._taxel_id = value

    @builtins.property
    def sensor_name(self):
        """Message field 'sensor_name'."""
        return self._sensor_name

    @sensor_name.setter
    def sensor_name(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'sensor_name' field must be of type 'str'"
        self._sensor_name = value

    @builtins.property
    def x(self):
        """Message field 'x'."""
        return self._x

    @x.setter
    def x(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'x' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'x' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._x = value

    @builtins.property
    def y(self):
        """Message field 'y'."""
        return self._y

    @y.setter
    def y(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'y' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'y' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._y = value

    @builtins.property
    def z(self):
        """Message field 'z'."""
        return self._z

    @z.setter
    def z(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'z' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'z' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._z = value

    @builtins.property
    def joint_x(self):
        """Message field 'joint_x'."""
        return self._joint_x

    @joint_x.setter
    def joint_x(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'joint_x' field must be of type 'str'"
        self._joint_x = value

    @builtins.property
    def joint_y(self):
        """Message field 'joint_y'."""
        return self._joint_y

    @joint_y.setter
    def joint_y(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'joint_y' field must be of type 'str'"
        self._joint_y = value

    @builtins.property
    def joint_z(self):
        """Message field 'joint_z'."""
        return self._joint_z

    @joint_z.setter
    def joint_z(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'joint_z' field must be of type 'str'"
        self._joint_z = value
