# Glossary


### Rehearsal

Testing the scenery package itself. 

### Scene

A __scene__ describes an event from the app perspective. It additionally describe the expected behavior of the app regarding this event by what we call a __directive__.

A scene can rely on a __substituable__ field, i.e. a field for which the value is placeholder that will be replaced by different potential values coming from what we call __cases__. This allows to check that the app behaves in a similar way with different values for this field. Such field can be used in the scene description or in a directive.

### Case

A case contains information that can be used to fill the substituable fields of a scene. A case has an id and a list of items. All cases applied to a given scene need to have a list of similar items. 



### Take

A __take__ is a scene in which all substituable fields have been replaced based on a particular case. We say that the take is the result of __shooting__ the scene with a given case.

Once shot, a directive is designated as a __check__.

### Manifest

A manifest contains all required information to build and run tests based on some scene(s) and case(s).