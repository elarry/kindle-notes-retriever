# -*- coding: utf-8 -*-

"""Extracts Amazon Kindle highlights and notes and generates LaTeX file from them.

UPDATE: As of recently, mechanize cannot be used to extract kindle notes.
UPDATE: Kindle note includes a notes exporter within the app itself that
allows you to email the notes to yourself.

Processes custom command tags from the notes associated with highlights
which specify an action to be taken. For example, the tag "#red" indicates
that the passage was highlighted in red, and is thus more important. As a
result this passage will be in bold in the LaTeX file.
If chapters/sections are tagged, a table of contents will be generated in the
LaTeX file.

Custom Commands:
"..." : Specifies that the current highlight is to be combined with
        the next highlight in the list
"Quote": Specifies that the current highlight is a quotation or a
         paraphrasing of some other author
"#red": Indicated that the highlight was colored in red in the Kindle app
"#part": Indicates that the highlight is the name of a part of the book
"#sec" : Indicates that the highlight is the name of the chapter
"#ch"  : Same as above (phased out)
"#subsec" : Indicates that the highlight is the name of a subsection
            of a chapter
"#subsubsec" : Indicates that the highlight is the name of a subsection
            of a subsection of a chapter

"""

import scrape_amazon
from bs4 import BeautifulSoup
import copy
import Tkinter
import tkFileDialog


def notes_to_latex(author_title0, notes_list):
    """Generate LaTeX file from extracted notes.
    """

    with open("tex/latex_template.tex", 'r') as f:
        tex_file = f.read()

    tex_file = tex_file.replace("_BOOK_AUTHOR", author_title0[0])
    tex_file = tex_file.replace("_BOOK_TITLE", author_title0[1])

    notes_flattened = sum(notes_list, [])  #ToDo: Fix. Clumsy and too fragile
    notes_output = '\n'.join(notes_flattened)
    notes_output = notes_output + "\n\\end{document}"

    tex_file_output = tex_file + "\n\n" + notes_output
    filename = "tex/" + author_title0[0] + " - " + author_title0[2] + ".tex"
    with open(filename, "w") as f:
        f.write(tex_file_output.encode('utf-8'))

    return


def extract_highlights_notes(soup_input):
    """Extracts highlights and notes from Amazon html file into a list.

    :param soup_input: Parsed html page with BeautifulSoup associated with a book
    :return: List of lists where the sub-list is of the form [*highlight*, *note*]
    """

    highlight_note = []
    highlight_div = soup_input.find_all('div', attrs={'class': "highlightRow yourHighlight"})
    for div in highlight_div:
        entry = []
        highlight0, note0 = div.find_all('span', attrs={'class': ['highlight', 'noteContent']})
        entry.append(highlight0.text)
        entry.append(note0.text)
        highlight_note.append(entry)
    return highlight_note


def extract_edit_stats(soup_input):
    """Extracts the editing statistics form the Kindle notes.
    Outputs a list of the number of passages highlighted, the number
    of notes, and the date of the last note addition to the kindle book.

    :param soup_input: Input file parsed with BeautifulSoup
    :return: [*number of highlights*, *Number of notes*, *Date of last edit*]
    """

    stats = soup_input.find('div', attrs={'class': "yourHighlightsStats"})
    last_edit = soup_input.find('div', attrs={'class': "lastHighlighted"})

    last_edit = last_edit.text
    stats = stats.text
    stats = stats.replace("\n", "")
    split_sentence = stats.find("You", 1)

    edit_stats = [stats[:split_sentence], stats[split_sentence:], last_edit]
    return edit_stats


def process_tag_combine(highlight_note):
    """Detects custom tag in notes of the form "...", which indicates
    that the following highlight should be considered as part of the
    highlight in question. This function combines the two highlights,
    and updates the notes accordingly.

    :param highlight_note: List of lists where each sub-list is of the
                           for [*highlight*, *note*]
    :return: updated highlight_note list
    """

    highlight_note_new = []
    highlight_note_iter = iter(highlight_note)  # Allows loop skipping
    for idx, entry in enumerate(highlight_note_iter):
        if entry[1].startswith("..."):
            entry_combined = highlight_note[idx][0] + "[...] " + highlight_note[idx + 1][0]
            print "Combining the following highlights:"
            print "1st: ", highlight_note[idx][0]
            print "2nd: ", highlight_note[idx + 1][0]
            highlight_note_new.append([entry_combined, highlight_note[idx + 1][1]])
            highlight_note_iter.next()  # Skip one step in the loop due to combination
        else:
            highlight_note_new.append(entry)
    return highlight_note_new


def process_tag_latex_red(highlight_note_input, emphasis="bold", emphasis_section=False):
    """Find tags marked "#red" which indicated and emphasised highlight.
    Insert latex code into the highlight to get the desired types of
    emphasis, which is indicated in the input "emphasis".

    :param highlight_note_input:
    :param emphasis: Choices: "bold", "italics","underline",large_font","red"
    :param emphasis_section: Collect emphasised highlights into a separate
                list, so that they can be inserted into the LaTeX file into
                a separate "important" section.
    :return: list, updated with latex code
    """

    highlight_note = copy.deepcopy(highlight_note_input)  # Keep tag processing independent of one another
    highlight_important = []

    stress = {"bold": ["\\textbf{", "}"],
              "italics": ["\\textit{", "}"],
              "underline": ["\\underline{", "}"],
              "large_font": ["\\begin{Large}\n", "\n\\end{Large}"],
              "red": ["\\textcolor{red}{", "}"]}

    for idx, entry in enumerate(highlight_note):
        if u'#red' in entry[1]:
            highlight0 = stress[emphasis][0] + entry[0] + stress[emphasis][1]
            highlight_note[idx] = [highlight0, '']
            highlight_important.append([highlight0, ''])

    if emphasis_section:
        return highlight_note, highlight_important
    else:
        return highlight_note


def process_tag_latex_section(highlight_note_input):
    """Add chapter sectioning following the hierarchical structure
    of LaTeX: part, section, subsection, subsubsection.
    Example: A highlight with an attached tag of "#sec", indicates
    that the highlight is the name of a section. That highlight will
    be enclosed by LaTeX code "\section{*section name*}" so that when
    compiled, the output PDF has clear section structure of the book.

    :param highlight_note_input: A list consisting of lists of the form
            [*highlight*, *note*]

    :return: List of lists, which is a modified version of the input
    """

    highlight_note = copy.deepcopy(highlight_note_input)  # Keep tag processing independent of one another

    for idx, entry in enumerate(highlight_note):
        if u'#part' in entry[1]:
            highlight0 = "\\part{" + entry[0] + "}"
            highlight_note[idx] = [highlight0, '']

        if (u'#sec' or u'#ch') in entry[1]:
            highlight0 = "\\section{" + entry[0] + "}"
            highlight_note[idx] = [highlight0, '']

        if u'#subsec' in entry[1]:
            highlight0 = "\\subsection{" + entry[0] + "}"
            highlight_note[idx] = [highlight0, '']

        if u'#subsubsec' in entry[1]:
            highlight0 = "\\subsubsection{" + entry[0] + "}"
            highlight_note[idx] = [highlight0, '']

    return highlight_note


def process_tag_remove_remaining(highlight_note_input):
    """Removes all remaining hash-tags #, which cause errors
    when compiling the LaTeX file

    :param highlight_note_input: A list consisting of lists of the form
            [...,[*highlight*, *note*],...]

    :return: Modified version of the input
    """

    highlight_note = copy.deepcopy(highlight_note_input)  # Keep tag processing independent of one another

    for idx, entry in enumerate(highlight_note):
        if u'#' in entry[1]:
            note_new = entry[1].replace("#", "")
            highlight_note[idx] = [entry[0], note_new]

    return highlight_note


def format_notes(highlight_note_input, note_differentiation=None):
    """Add a marker "Note: " to the beginning of notes, which differentiate
    a note from the text of a highlight.
    Also
    NOTE: This function should probably be run last.

    :param highlight_note_input: Input list of highlights and notes
    :param note_differentiation: Select additional ways to differentiate
           the text of notes from the text of highlights. Optional
           parameters include changing stile, size or color of note.
            Options: "italics", "small", "footnotesize", "gray"

    :return: Modified version of input
    """
    note_formatting = {"italics": ["\\textit{", "}"],
                       "small": ["{\\small ", "}"],
                       "footnotesize": ["{\\footnotesize ", "}"],
                       "gray": ["\\textcolor{gray}{", "}"]}
    highlight_note = copy.deepcopy(highlight_note_input)  # Keep tag processing independent of one another
    for idx, entry in enumerate(highlight_note):
        if entry[1] != '':
            note_new = "Note: " + entry[1]
            if note_differentiation != None:
                note_new = note_formatting[note_differentiation][0] +\
                           note_new + note_formatting[note_differentiation][1]
            highlight_note[idx] = [entry[0], note_new]

    return highlight_note


if __name__ == "__main__":
    scrape_amazon.scrape_amazon_notes()  # Retrieve kindle notes from web

    # Choose note you wish to process
    note_source = "html_files/"
    root = Tkinter.Tk()
    root.update()
    book_source = tkFileDialog.askopenfilename(initialdir=note_source)
    root.withdraw()

    author_title = scrape_amazon.extract_author_title(book_source)
    soup = BeautifulSoup(open(book_source))
    notes = extract_highlights_notes(soup)

    # Process custom tags which generate table of contents, and output certain passages in bold font
    notes = process_tag_combine(notes)
    notes = process_tag_latex_red(notes, "bold")
    notes = process_tag_latex_section(notes)
    notes = process_tag_remove_remaining(notes)

    # Generate LaTeX file
    notes_to_latex(author_title, notes)
