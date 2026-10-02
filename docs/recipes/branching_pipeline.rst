Branching pipeline
^^^^^^^^^^^^^^^^^^

One extraction can feed several destination tables. A :ref:`transform
<transform>` function can return a tuple of output rows for each input row.
The pipeline separates these outputs and passes each branch to
:func:`load() <etlhelper.load>`.

This example applies two checks to bird records. Every bird produces a size
check, while the swimming-bird branch only includes birds matching the name
check. ``None`` indicates that a row has no output for that branch. Replace
these illustrative checks with validation rules for your own data.

.. literalinclude:: ../code_demos/recipes/branching_pipeline.py
   :language: python

Run the example from the repository root with:

.. code-block:: shell

   python docs/code_demos/recipes/branching_pipeline.py

The example uses in-memory SQLite databases and requires no database server.
It stores four size checks and two swimming-bird records. Its first chunk has
no swimming birds: passing the empty list to ``load`` inserts no rows, and
later chunks still populate that branch. An empty source produces no chunks
and leaves both destination tables empty.

:func:`iter_chunks() <etlhelper.iter_chunks>` limits the input rows held in
memory at a time. The transformed outputs are collected only for the current
chunk, so each branch can contain a different number of rows. Use separate
destination connections in the two ``load`` calls to send the branches to
different databases. Each call commits its own output by default. When both
tables use the same destination connection, pass ``commit_chunks=False`` to
both loads and commit that connection only after both succeed. Separate
destinations have independent transactions.
