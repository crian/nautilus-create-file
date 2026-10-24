project(
  'nautilus-create-file',
  version: '1.0.0',
  license: 'GPL-3.0-or-later',
  meson_version: '>= 0.59.0',
)

i18n = import('i18n')

install_data(
  'nautilus-create-file.py',
  install_dir: get_option('datadir') / 'nautilus-python' / 'extensions',
)

subdir('po')
