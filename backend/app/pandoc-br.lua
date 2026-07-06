-- Wandelt rohe <br>-Tags in echte Zeilenumbrüche um.
-- Nötig, weil der docx-Writer von pandoc rohes HTML verwirft —
-- Zellinhalte mit <br>-Umbrüchen verkleben sonst zu einer Zeile.
function RawInline(el)
  if el.format == 'html' and el.text:match('^<br%s*/?>$') then
    return pandoc.LineBreak()
  end
end
