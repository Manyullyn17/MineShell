from textual.app import App
from textual.theme import Theme
from screens.main_menu import MainMenu

deepslate_theme = Theme(
    name='deepslate',
    primary='#4da08f',         # muted mossy green (accent)
    secondary='#6ab19e',       # highlight (hover)
    accent='#4da08f',          # same as primary accent
    foreground='#e0e0e0',      # soft light gray (main text)
    background='#1b1e26',      # slightly bluish dark gray (background)
    success='#00aa69',         # reusing accent green for success
    warning='#ebb655',         # dimmed yellow (warning)
    error='#df545f',           # subtle red (error)
    surface='#232834',         # lighter inner backgrounds (panel/bg)
    panel='#232834',           # same as surface
    dark=True,
    variables={
        'block-cursor-text-style': 'none',
        'footer-key-foreground': '#4da08f',
        'input-selection-background': '#6ab19e 35%',
        # you can add more CSS variables if needed
    },
)

class MineShell(App):
    def on_mount(self) -> None:
        self.register_theme(deepslate_theme)
        self.theme = 'deepslate'
        self.push_screen(MainMenu())

if __name__ == '__main__':
    MineShell().run()


# TO-DO:
# - make naming make sense and consistent

