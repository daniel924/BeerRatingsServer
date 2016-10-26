"""`appengine_config` gets loaded when starting a new application instance."""
import os
import vendor
# insert `lib` as a site directory so our `main` module can load
# third-party libraries, and override built-ins with newer
# versions.
vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

