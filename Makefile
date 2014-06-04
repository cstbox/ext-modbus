# CSTBox framework
#
# Makefile for building the Debian distribution package containing the
# Modbus devices support.
#
# author = Eric PASCUAL - CSTB (eric.pascual@cstb.fr)

# name of the CSTBox module
MODULE_NAME=ext-modbus

include $(CSTBOX_DEVEL_HOME)/lib/makefile-dist.mk

copy_files: \
	check_metadata_files \
	copy_devices_metadata_files \
	copy_bin_files \
	copy_python_files \
	copy_init_scripts \
	copy_python_support_pkgs

