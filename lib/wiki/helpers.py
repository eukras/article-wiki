# Reuasble formatting tools.

from jinja2 import Environment

from lib.wiki.utils import trim

def web_buttons(user_slug: str, doc_slug: str) -> str:
    if doc_slug is None:
        return ""
    env = Environment(autoescape=True)
    tpl = env.from_string(trim("""
    <div class="web-only text-center no-print">
        <table>
            <tbody>
                <tr>
                    <td class="nav-label text-center">
                        <a
                            class="button feature"
                            href="/"
                        >
                            <i class="fa fa-home"></i>&nbsp; Home
                        </a>
                    </td>
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
                    <td class="nav-label text-center">
                        <a class="button feature button-themes">
                            <i class="fa fa-adjust"></i>&nbsp; Theme
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
