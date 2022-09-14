# Hyperchalk – Excalidraw for LTI

Hyperchalk is a port of the [Excalidraw](https://excalidraw.com) app to support LTI and data
collection, enabling its usage for learning analytics in LMS courses.

If you use Hyperchalk in your scientific work, please cite this paper ([biblatex here][bib]):

> Lukas Menzel, Sebastian Gombert, Daniele Di Mitri and Hendrik Drachsler. "Superpowers in the
> Classroom: Hyperchalk is an Online Whiteboard for Learning Analytics Data Collection". In:
> Proceedings of the 17th European Conference on Technology Enhanced Learning. Mai 2022.

[bib]: https://github.com/Hyperchalk/Hyperchalk/blob/main/citation.bib

## Documentation

**[View the documentation page](https://hyperchalk.github.io/guide/)**

## Known Issues

### Cloning LMS-Courses with Hyperchalk content

When a course (C0) is cloned (C1) in an LMS, Hyperchalk will detect that and clone any Whiteboards
set up whithin the course C0 to C1. However, when a cloned course (C1) gets cloned again (C2),
Hyperchalk will register that clone C2 as a clone of the original course C0. It will thus not
"clone-clone" any changes made to the clone C1 to C2, but it will copy C0 to C2 instead.

There is no easy fix for this because this would need a possibility to change LTI custom data after
the LTI tool configuration process when Hyperchalk is set up for the first time in a course C0. Even
the cloning detection mechanism required an additional table in the database and a lot of code for
such a simple feature.
