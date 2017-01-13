import sublime
import sublime_plugin

from .src.registry import FormatRegistry


def source_file(view):
    scope = view.scope_name(0) or ''
    return next(iter(scope.split(' ')))


def queue_command(callback):
    sublime.set_timeout(callback, 100)


def reload(view):
    queue_command(lambda: view.run_command('revert'))


def print_error(error):
    print('Format:', error)


registry = FormatRegistry()


class FormatSelectionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        formatter = registry.by_source(source_file(self.view))
        if formatter is None:
            print_error('No formatter for source file')
            return

        for region in self.view.sel():
            if region.empty():
                continue

            selection = self.view.substr(region)
            output, error = formatter.format(input=selection)
            if not error:
                self.view.replace(edit, region, output)
            else:
                print_error(error)
        reload(self.view)


class FormatFileCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        formatter = registry.by_source(source_file(self.view))
        if formatter is None:
            print_error('No formatter for source file')
            return

        output, error = formatter.format(file=self.view.file_name())
        if not error:
            reload(self.view)
        else:
            print_error(error)


class FormatListener(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        formatter = registry.by_source(source_file(view))
        if formatter and formatter.format_on_save:
            view.run_command('format_file')


class ToggleFormatOnSaveCommand(sublime_plugin.ApplicationCommand):
    def is_checked(self, name=None):
        if name is None:
            formatters = registry.all
            enabled = [x for x in formatters if x.format_on_save]
            return len(enabled) == len(formatters)
        else:
            formatter = registry.by_name(name)
            return formatter.format_on_save if formatter else False

    def run(self, name=None, value=None):
        if name is None:
            self.toggle_all()
        else:
            self.toggle(name, value)

    def toggle(self, name, value):
        formatter = registry.by_name(name)
        if formatter is not None:
            current = formatter.format_on_save
            formatter.format_on_save = not current if value is None else value

    def toggle_all(self):
        formatters = registry.all
        enabled = [x for x in formatters if x.format_on_save]
        enable = len(enabled) < len(formatters)
        for formatter in formatters:
            formatter.format_on_save = enable


class ManageFormatOnSaveCommand(sublime_plugin.WindowCommand):
    def run(self, which=None):
        enabled = which == 'enabled'
        items = [[x.name] for x in registry.all if x.format_on_save == enabled]

        def callback(selection):
            if selection >= 0 and selection < len(items):
                args = {'name': items[selection][0]}
                self.window.run_command('toggle_format_on_save', args)

        queue_command(lambda: self.window.show_quick_panel(items, callback))
