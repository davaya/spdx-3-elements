# SPDX Version 3 Elements, Transfer Units, and Documents
The [SPDX v3 logical model](images/spdx-3-model-2022-05-17.png) depicts the Elements used to build an SPDX
knowledge graph.
* Each element value is uniquely identified by an IRI
* Each element value is immutable - once an IRI has been assigned to a value, the IRI cannot be reused and the value cannot be changed
* Each element is independent - no element depends on the value of any other element

The independence property ensures that each logical element instance can be serialized separately into
a data instance, and that data instance is hashable. A collection of element instances can also be serialized
together into a data file referred to as a *transfer unit*, in order to reduce size and enable an
integrity check value to cover the entire collection.

[Logical Elements](images/logical-elements.png)

[Transfer Units](images/transfer-units.png)