from packaging.version import Version, InvalidVersion

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.events import Resize
from textual.widgets import Label, Button, Collapsible, SelectionList, Static

from helpers import CustomModal, FocusNavigationMixin

class FilterModal(FocusNavigationMixin, CustomModal[dict]):
    """A reusable modal to select values to filter by."""
    CSS_PATH = 'styles/filter_modal.tcss'
    BINDINGS = [
            Binding('q', 'back', show=False),
            Binding('escape', 'esc', show=False),
            Binding('r', "reset", show=False),
        ] + FocusNavigationMixin.BINDINGS

    first_open = True

    def __init__(self, choices: list[dict[str, str | list[str]]], filter_columns: list[str] | None = None):
        super().__init__()
        self.choices = choices
        self.column_names = list(choices[0])
        self.filter_columns = filter_columns if filter_columns else self.column_names
        self.filters: dict[str, list[str]] = {}
        self.navigation_map: dict[str, dict] = {}
        self.select_ids = []
        self.collapsible_ids = []

    def compose(self) -> ComposeResult:
        self.grid = Grid(id='filter-grid')
        yield self.grid

    def on_mount(self):
        row_size = ['auto'] * len(self.filter_columns) + ['1fr', '3']
        self.grid.styles.grid_rows = ' '.join(row_size)
        self.grid.border_title = 'Filter Table'
        self.grid.border_subtitle = 'r to reset'

        unique_values = {
            key: list({
                elem
                for row in self.choices
                for cell in (row[key] if isinstance(row[key], list) else [row[key]])
                for elem in ([cell] if isinstance(cell, str) else cell)  # flatten one level
            })
            for key in self.filter_columns
        }

        def sort_key(v: str):
            try: # try sorting by version
                return Version(v)
            except InvalidVersion:
                return (1, v.lower())  # if not, use alphabetical for text

        self.collapsible_ids = []
        for column in self.filter_columns:
            first = unique_values[column][0].rsplit('.')[0]
            reverse = True if first.isdigit() else False
            self.grid.mount(Label(column.replace('_', ' ').title(), classes='filter label'))
            self.grid.mount(
                Collapsible(
                    SelectionList(
                        *((v, v) for v in sorted(unique_values[column], key=sort_key, reverse=reverse)),
                        compact=True,
                        id=f'filter-{column}',
                        classes='filter selectionlist'
                        ),
                    title='All',
                    id=f'{column}-collapsible',
                    classes='filter collapsible'
                    )
                )
            self.select_ids.append(f'filter-{column}')
            self.collapsible_ids.append(f'{column}-collapsible')

        for i, select_id in enumerate(self.select_ids):
            nav = {"left": "", "right": ""}

            # Up
            if i == 0:
                nav["up"] = ""
            else:
                nav["up"] = self.collapsible_ids[i - 1]

            # Down
            if i == len(self.select_ids) - 1:
                nav["down"] = 'filter-done-button'
            else:
                nav["down"] = self.collapsible_ids[i + 1]

            self.navigation_map[select_id] = nav
        
        self.navigation_map['filter-done-button'] = {'left': 'filter-back-button', 'up': self.collapsible_ids[-1], 'down': '', 'right': ''}
        self.navigation_map['filter-back-button'] = {'left': '', 'up': self.collapsible_ids[-1], 'down': '', 'right': 'filter-done-button'}

        self.grid.mount(Static(id='filter-spacer', classes='filter spacer'))
        self.grid.mount(Button('Back', id='filter-back-button', classes='filter button'))
        self.grid.mount(Button('Done', id='filter-done-button', classes='filter button'))

    @on(Resize)
    def on_resize(self, event: Resize):
        self.resize_selectionlist()
        self.grid.styles.width = int(self.size.width * 0.5)
        self.grid.styles.height = int(self.size.height * 0.8)

    def resize_selectionlist(self):
        total_rows_height = len(self.filter_columns) * 3 + 4 # number of collapsibles * collapsed height + button row height
        available_height = int(self.app.size.height * 0.8 - total_rows_height - 2)
        selectionlist_height = max(available_height - 1, 3) # -1 for extra row from collapsible expanding, minimum of 3

        for select in self.query(SelectionList):
            select.styles.max_height = selectionlist_height

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case 'filter-back-button':
                self.action_back()
            case 'filter-done-button':
                self.action_done()

    @on(SelectionList.SelectedChanged)
    def on_selection_changed(self) -> None:
        for select_id in self.select_ids:
            select = self.query_one(f'#{select_id}', SelectionList)
            if select.selected:
                self.filters[select_id.rsplit('-', 2)[-1]] = sorted(select.selected)
            else:
                self.filters.pop(select_id.rsplit('-', 2)[-1], None)
            if select.parent:
                if isinstance(select.parent.parent, Collapsible):
                    if select.selected:
                        select.parent.parent.title = ', '.join(sorted(select.selected))
                    else:
                        select.parent.parent.title = 'All'

    def on_collapsible_expanded(self) -> None:
        if self.first_open:
            self.resize_selectionlist()
            self.first_open = False
        focused = self.focused
        collapsible: Collapsible | None = None
        widget = focused
        while widget:
            if isinstance(widget, Collapsible):
                collapsible = widget
                break
            widget = widget.parent
        if collapsible and collapsible.id:
            for id in self.collapsible_ids:
                if id != collapsible.id:
                    self.query_one(f'#{id}', Collapsible).collapsed = True

    def action_focus_move(self, direction: str):
        # - if in collapsible, up should focus collapsible, down should focus widget below collapsible
        focused = self.focused
        if not focused:
            return
        collapsible = next((a for a in focused.ancestors if isinstance(a, Collapsible)), None)
        if collapsible:
            selectlist = collapsible.query_one(SelectionList)
            if not selectlist:
                return
            if not collapsible.collapsed and direction == 'down': # if pressing down on expanded collapsible -> focus selectlist inside
                selectlist.focus()
                return
            else: # else set focused to selectlist and let navigation_map take over
                focused = selectlist
                
        if not focused.id:
            return
        try:
            next_id = self.navigation_map.get(focused.id, {}).get(direction)
            if next_id:
                next_widget = self.query_one(f'#{next_id}')
                if isinstance(next_widget, Collapsible):
                    next_widget.query("CollapsibleTitle").focus()
                else:
                    next_widget.focus()
        except Exception as e:
            self.notify(f"Failed to move focus. {e}", severity='error', timeout=5)

    def action_esc(self):
        focused = self.focused
        # Check if focused widget is a collapsible or inside one
        collapsible = None
        widget = focused
        while widget:
            if isinstance(widget, Collapsible):
                collapsible = widget
                break
            widget = widget.parent

        if collapsible and not collapsible.collapsed:
            collapsible.collapsed = True
            collapsible.children[0].focus()
        else:
            self.action_back()

    def action_back(self):
        self.dismiss()

    def action_done(self):
        self.dismiss(self.filters)

    def action_reset(self):
        for id in self.select_ids:
            self.query_one(f'#{id}', expect_type=SelectionList).deselect_all()
        self.filters = {}
