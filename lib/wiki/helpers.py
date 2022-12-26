# Reuasble formatting tools.

from jinja2 import Environment

from lib.wiki.utils import trim

def web_buttons(user_slug: str, doc_slug: str) -> str:
    if doc_slug is None:
        return ""
    env = Environment(autoescape=True)
    tpl = env.from_string(trim("""
    <div class="button-menu web-only text-center no-print">
        <table>
            <tbody>
                <tr>
                    <td class="nav-label text-center">
                        <a
                            class="button feature"
                            onClick="window.print();"
                        >
                            <i class="fa fa-print"></i>&nbsp; Print (to PDF?)
                        </a>
                    </td>
                    <td class="nav-label text-center">
                        <a
                            class="button feature"
                            href="/epub/{{user_slug}}/{{doc_slug}}"
                        >
                            <i class="fa fa-book"></i>&nbsp; Download (as .EPUB)
                        </a>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """))
    return tpl.render(
         user_slug=user_slug,
         doc_slug=doc_slug,
        )
