#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Completion evaluation code for Python"""

from codeintel2.common import *
from codeintel2.tree import TreeEvaluator


class PythonTreeEvaluator(TreeEvaluator):
    def eval_cplns(self):
        self.log_start()
        start_scoperef = self.get_start_scoperef()
        self.info("start scope is %r", start_scoperef)
        #if self.trg.type == 'available-classes':
        #    return self._available_classes(start_scoperef, self.trg.extra["consumed"])
        hit = self._hit_from_citdl(self.expr, start_scoperef)
        return list(self._members_from_hit(hit))

    def eval_calltips(self):
        self.log_start()
        start_scoperef = self.get_start_scoperef()
        self.info("start scope is %r", start_scoperef)
        hit = self._hit_from_citdl(self.expr, start_scoperef)
        return [ self._calltip_from_hit(hit) ]

    def eval_defns(self):
        self.log_start()
        start_scoperef = self.get_start_scoperef()
        self.info("start scope is %r", start_scoperef)
        hit = self._hit_from_citdl(self.expr, start_scoperef, defn_only=True)
        return [ self._defn_from_hit(hit) ]

    #def _available_classes(self, scoperef, consumed):
    #    matches = set()
    #    blob = scoperef[0] # XXX??
    #    for elem in blob:
    #        if elem.tag == 'scope' and elem.get('ilk') == 'class':
    #            matches.add(elem.get('name'))
    #    matches.difference_update(set(consumed))
    #    matches_list = sorted(list(matches))
    #    return [('class', m) for m in matches_list]
    
    def _tokenize_citdl_expr(self, citdl):
        for token in citdl.split('.'):
            if token.endswith('()'):
                yield token[:-2]
                yield '()'
            else:
                yield token
    def _join_citdl_expr(self, tokens):
        return '.'.join(tokens)

    def _calltip_from_func(self, elem, scoperef, class_name=None):
        # See "Determining a Function CallTip" in the spec for a
        # discussion of this algorithm.
        signature = elem.get("signature")
        ctlines = []
        if not signature:
            name = class_name or elem.get("name")
            ctlines = [name + "(...)"]
        else:
            ctlines = signature.splitlines(0)
        doc = elem.get("doc")
        if doc:
            ctlines += doc.splitlines(0)
        return '\n'.join(ctlines)

    def _calltip_from_class(self, elem, scoperef):
        # If the class has a defined signature then use that.
        signature = elem.get("signature")
        if signature:
            doc = elem.get("doc")
            ctlines = signature.splitlines(0)
            if doc:
                ctlines += doc.splitlines(0)
            return '\n'.join(ctlines)
        else:
            ctor_hit = self._ctor_hit_from_class(elem, scoperef)
            if ctor_hit and (ctor_hit[0].get("doc")
                             or ctor_hit[0].get("signature")):
                self.log("ctor is %r on %r", *ctor_hit)
                return self._calltip_from_func(ctor_hit[0], ctor_hit[1],
                                               class_name=elem.get("name"))
                
            else:
                doc = elem.get("doc")
                if doc:
                    ctlines = [ln for ln in doc.splitlines(0) if ln]
                else:
                    ctlines = [elem.get("name") + "()"]
                return '\n'.join(ctlines)

    def _ctor_hit_from_class(self, elem, scoperef):
        """Return the Python ctor for the given class element, or None."""
        if "__init__" in elem.names:
            class_scoperef = (scoperef[0], scoperef[1]+[elem.get("name")])
            return elem.names["__init__"], class_scoperef
        else:
            for classref in elem.get("classrefs", "").split():
                try:
                    basehit = self._hit_from_type_inference(classref, scoperef)
                except CodeIntelError, ex:
                    self.warn(str(ex))
                else:
                    ctor_hit = self._ctor_hit_from_class(*basehit)
                    if ctor_hit:
                        return ctor_hit
        return None

    def _calltip_from_hit(self, hit):
        # TODO: compare with CitadelEvaluator._getSymbolCallTips()
        elem, scoperef = hit
        if elem.tag == "variable":
            XXX
        elif elem.tag == "scope":
            ilk = elem.get("ilk")
            if ilk == "function":
                calltip = self._calltip_from_func(elem, scoperef)
            elif ilk == "class":
                calltip = self._calltip_from_class(elem, scoperef)
            else:
                raise NotImplementedError("unexpected scope ilk for "
                                          "calltip hit: %r" % elem)
        else:
            raise NotImplementedError("unexpected elem for calltip "
                                      "hit: %r" % elem)
        return calltip

    def _members_from_elem(self, elem):
        """Return the appropriate set of autocomplete completions for
        the given element. Typically this is just one, but can be more for
        '*'-imports
        """
        members = set()
        if elem.tag == "import":
            alias = elem.get("alias")
            symbol_name = elem.get("symbol")
            module_name = elem.get("module")
            if symbol_name:
                # This can fail as follows:
                #   foo.py:          import bar; bar.<|>
                #   bar/__init__.py: import blam
                #   bar/blam.py
                # 'blam.py' should be imported to report it as a
                # completion for 'bar.<|>' in foo.py. However the
                # <currdirlib> won't find it because we are using
                # foo.py's cwd, not the bar directory.
                #
                # The right answer is to have a buf for bar/__init__.py
                # and ask it to do the import (it has its own .libs).
                #
                # TODO: What about having
                #   buf.members_from_elem(elem, trg.lang, ctlr)?
                #   Pass around scoperef. Scoperef becomes (buf, lang,
                #   lpath). 
                import_handler = self.citadel.import_handler_from_lang(self.trg.lang)
                try:
                    blob = import_handler.import_blob_name(
                                module_name, self.buf.libs, self.ctlr)
                except:
                    self.warn("limitation in handling imports in imported modules")
                    raise

                if symbol_name == "*":
                    for m_name, m_elem in blob.names.items():
                        m_type = m_elem.get("ilk") or m_elem.tag
                        members.add( (m_type, m_name) )
                elif symbol_name in blob.names:
                    symbol = blob.names[symbol_name]
                    member_type = (symbol.get("ilk") or symbol.tag)
                    members.add( (member_type, alias or symbol_name) )
                else:
                    hit, nconsumed \
                        = self._hit_from_elem_imports([symbol_name], blob)
                    if hit:
                        symbol = hit[0]
                        member_type = (symbol.get("ilk") or symbol.tag)
                        members.add( (member_type, alias or symbol_name) )
                    else:
                        self.warn("could not resolve %r", elem)
            else:
                cpln_name = alias or module_name.split('.', 1)[0]
                members.add( ("module", cpln_name) )
        else:
            members.add( (elem.get("ilk") or elem.tag, elem.get("name")) )
        return members

    def _members_from_hit(self, hit):
        elem, scoperef = hit
        members = set()
        for child in elem:
            if "__hidden__" not in child.get("attributes", "").split():
                try:
                    members.update(self._members_from_elem(child))
                except CodeIntelError, ex:
                    self.warn("%s (skipping members for %s)", ex, child)
        if elem.get("ilk") == "class":
            for classref in elem.get("classrefs", "").split():
                try:
                    subhit = self._hit_from_type_inference(classref, scoperef)
                except CodeIntelError, ex:
                    # Continue with what we *can* resolve.
                    self.warn(str(ex))
                else:
                    members.update(self._members_from_hit(subhit))
        return members

    def _hit_from_citdl(self, expr, scoperef, defn_only=False):
        """Resolve the given CITDL expression (starting at the given
        scope) down to a non-import/non-variable hit.
        """
        self._check_infinite_recursion(expr)
        tokens = list(self._tokenize_citdl_expr(expr))
        #self.log("expr tokens: %r", tokens)

        # First part...
        hit, nconsumed = self._hit_from_first_part(tokens, scoperef)
        if not hit:
            #TODO: Add the fallback Buffer-specific near-by hunt
            #      for a symbol for the first token. See my spiral-bound
            #      book for some notes.
            raise CodeIntelError("could not resolve first part of '%s'" % expr)
        self.debug("_hit_from_citdl: first part: %r -> %r",
                   tokens[:nconsumed], hit)

        # ...the remainder.
        remaining_tokens = tokens[nconsumed:]
        while remaining_tokens:
            self.debug("_hit_from_citdl: resolve %r on %r in %r",
                       remaining_tokens, *hit)
            if remaining_tokens[0] == "()":
                new_hit = self._hit_from_call(*hit)
                nconsumed = 1
            else:
                new_hit, nconsumed \
                    = self._hit_from_getattr(remaining_tokens, *hit)
            remaining_tokens = remaining_tokens[nconsumed:]
            hit = new_hit

        # Resolve any variable type inferences.
        #TODO: Need to *recursively* resolve hits.
        elem, scoperef = hit
        if elem.tag == "variable" and not defn_only:
            elem, scoperef = self._hit_from_variable_type_inference(elem, scoperef)

        self.info("'%s' is %s on %s", expr, elem, scoperef)
        return (elem, scoperef)

    def _hit_from_first_part(self, tokens, scoperef):
        """Find a hit for the first part of the tokens.

        Returns (<hit>, <num-tokens-consumed>) or (None, None) if could
        not resolve.

        Example for 'os.sep':
            tokens: ('os', 'sep')
            retval: ((<variable 'sep'>,  (<blob 'os', [])),   1)
        Example for 'os.path':
            tokens: ('os', 'path')
            retval: ((<import os.path>,  (<blob 'os', [])),   2)
        """
        first_token = tokens[0]
        self.log("find '%s ...' starting at %s:", first_token, scoperef)

        # pythoncile will sometimes give a citdl expression of "__builtins__",
        # check for this now, bug:
        #   http://bugs.activestate.com/show_bug.cgi?id=71972
        if first_token == "__builtins__":
            # __builtins__ is the same as the built_in_blob, return it.
            scoperef = (self.built_in_blob, [])
            return (self.built_in_blob, scoperef), 1

        while 1:
            elem = self._elem_from_scoperef(scoperef)
            if first_token in elem.names:
                #TODO: skip __hidden__ names
                self.log("is '%s' accessible on %s? yes: %s",
                         first_token, scoperef, elem.names[first_token])
                return (elem.names[first_token], scoperef), 1

            hit, nconsumed \
                = self._hit_from_elem_imports(tokens, elem)
            if hit is not None:
                self.log("is '%s' accessible on %s? yes: %s",
                         '.'.join(tokens[:nconsumed]), scoperef, hit[0])
                return hit, nconsumed

            self.log("is '%s' accessible on %s? no", first_token, scoperef)
            scoperef = self.parent_scoperef_from_scoperef(scoperef)
            if not scoperef:
                return None, None

    def _hit_from_elem_imports(self, tokens, elem):
        """See if token is from one of the imports on this <scope> elem.

        Returns (<hit>, <num-tokens-consumed>) or (None, None) if not found.
        XXX import_handler.import_blob_name() calls all have potential
            to raise CodeIntelError.
        """
        #PERF: just have a .import_handler property on the evalr?
        import_handler = self.citadel.import_handler_from_lang(self.trg.lang)
        libs = self.buf.libs

        #PERF: Add .imports method to ciElementTree for quick iteration
        #      over them. Or perhaps some cache to speed this method.
        #TODO: The right answer here is to not resolve the <import>,
        #      just return it. It is complicated enough that the
        #      construction of members has to know the original context.
        #      See the "Foo.mypackage.<|>mymodule.yo" part of test
        #      python/cpln/wacky_imports.
        #      XXX Not totally confident that this is the right answer.
        first_token = tokens[0]
        self._check_infinite_recursion(first_token)
        for imp_elem in (i for i in elem if i.tag == "import"):
            self.debug("'%s ...' from %r?", tokens[0], imp_elem)
            alias = imp_elem.get("alias")
            symbol_name = imp_elem.get("symbol")
            module_name = imp_elem.get("module")

            if symbol_name:
                # from module import symbol, from module import symbol as alias
                # from module import submod, from module import submod as alias
                if (alias and alias == first_token) \
                   or (not alias and symbol_name == first_token):
                    # Try 'from module import symbol/from module import
                    # symbol as alias' first.
                    try:
                        blob = import_handler.import_blob_name(
                                    module_name, libs, self.ctlr)
                        if symbol_name in blob.names:
                            return (blob.names[symbol_name], (blob, [])),  1
                        else:
                            hit, nconsumed = self._hit_from_elem_imports(
                                [first_token] + tokens[1:], blob)
                            if hit: 
                                return hit, nconsumed
                    except CodeIntelError:
                        pass

                    # That didn't work, try 'from module import
                    # submod/from module import submod as alias'.
                    submodule_name = import_handler.sep.join(
                                        [module_name, symbol_name])
                    try:
                        subblob = import_handler.import_blob_name(
                                    submodule_name, libs, self.ctlr)
                        return (subblob, (subblob, [])), 1
                    except CodeIntelError:
                        # That didn't work either. Give up.
                        self.warn("could not import '%s' from %s",
                                  first_token, imp_elem)

                # from module import *
                elif symbol_name == "*":
                    try:
                        blob = import_handler.import_blob_name(
                                    module_name, libs, self.ctlr)
                    except CodeIntelError:
                        pass # don't freak out: might not be our import anyway
                    else:
                        try:
                            hit, nconsumed = self._hit_from_getattr(
                                                tokens, blob, (blob, []))
                        except CodeIntelError:
                            pass
                        else:
                            if hit:
                                return hit, nconsumed

            elif (alias and alias == first_token) \
                 or (not alias and module_name == first_token):
                blob = import_handler.import_blob_name(
                            module_name, libs, self.ctlr)
                return (blob, (blob, [])),  1

            elif '.' in module_name:
                # E.g., might be looking up ('os', 'path', ...) and
                # have <import os.path>.
                module_tokens = module_name.split('.')
                if module_tokens == tokens[:len(module_tokens)]:
                    # E.g. tokens:   ('os', 'path', ...)
                    #      imp_elem: <import os.path>
                    #      return:   <blob 'os.path'> for first two tokens
                    blob = import_handler.import_blob_name(
                                module_name, libs, self.ctlr)
                    #XXX Is this correct scoperef for module object?
                    return (blob, (blob, [])),  len(module_tokens)
                else:
                    # E.g. tokens:   ('os', 'sep', ...)
                    #      imp_elem: <import os.path>
                    #      return:   <blob 'os'> for first token
                    for i in range(len(module_tokens)-1, 0, -1):
                        if module_tokens[:i] == tokens[:i]:
                            blob = import_handler.import_blob_name(
                                        '.'.join(module_tokens[:i]),
                                        libs, self.ctlr)
                            #XXX Is this correct scoperef for module object?
                            return (blob, (blob, [])),  i

        return None, None

    def _hit_from_call(self, elem, scoperef):
        """Resolve the function call inference for 'elem' at 'scoperef'."""
        # This might be a variable, in that case we keep resolving the variable
        # until we get to the final function/class element that is to be called.
        while elem.tag == "variable":
            elem, scoperef = self._hit_from_variable_type_inference(elem, scoperef)
        ilk = elem.get("ilk")
        if ilk == "class":
            # Return the class element.
            self.log("_hit_from_call: resolved to class '%s'", elem.get("name"))
            return (elem, scoperef)
        if ilk == "function":
            citdl = elem.get("returns")
            if citdl:
                self.log("_hit_from_call: function with citdl %r",
                         citdl)
                # scoperef has to be set to the function called
                func_scoperef = (scoperef[0], scoperef[1]+[elem.get("name")])
                return self._hit_from_citdl(citdl, func_scoperef)
        raise CodeIntelError("no return type info for %r" % elem)

    def _hit_from_getattr(self, tokens, elem, scoperef):
        """Return a hit for a getattr on the given element.

        Returns (<hit>, <num-tokens-consumed>) or raises an CodeIntelError.

        Typically this just does a getattr of tokens[0], but handling
        some multi-level imports can result in multiple tokens being
        consumed.
        """
        #TODO: On failure, call a hook to make an educated guess. Some
        #      attribute names are strong signals as to the object type
        #      -- typically those for common built-in classes.
        first_token = tokens[0]
        self.log("resolve getattr '%s' on %r in %r:", first_token,
                 elem, scoperef)
        if elem.tag == "variable":
            elem, scoperef = self._hit_from_variable_type_inference(elem, scoperef)

        assert elem.tag == "scope"
        ilk = elem.get("ilk")
        if ilk == "function":
            # Internal function arguments and variable should
            # *not* resolve. And we don't support function
            # attributes.
            pass
        elif ilk == "class":
            attr = elem.names.get(first_token)
            if attr is not None:
                self.log("attr is %r in %r", attr, elem)
                # update the scoperef, we are now inside the class.
                scoperef = (scoperef[0], scoperef[1] + [elem.get("name")])
                return (attr, scoperef), 1

            self.debug("look for %r from imports in %r", tokens, elem)
            hit, nconsumed \
                = self._hit_from_elem_imports(tokens, elem)
            if hit is not None:
                return hit, nconsumed

            for classref in elem.get("classrefs", "").split():
                try:
                    self.log("is '%s' from base class: %r?", first_token,
                             classref)
                    base_elem, base_scoperef \
                        = self._hit_from_type_inference(classref, scoperef)
                    return self._hit_from_getattr(tokens, base_elem,
                                                  base_scoperef)
                except CodeIntelError, ex:
                    self.log("could not resolve '%s' getattr on base class %r",
                             first_token, base_elem)
                    # Was not available, try the next class then.
        elif ilk == "blob":
            attr = elem.names.get(first_token)
            if attr is not None:
                self.log("attr is %r in %r", attr, elem)
                return (attr, scoperef), 1

            hit, nconsumed \
                = self._hit_from_elem_imports(tokens, elem)
            if hit is not None:
                return hit, nconsumed
        else:
            raise NotImplementedError("unexpected scope ilk: %r" % ilk)

        raise CodeIntelError("could not resolve '%s' getattr on %r in %r"
                             % (first_token, elem, scoperef))

    def _hit_from_variable_type_inference(self, elem, scoperef):
        """Resolve the type inference for 'elem' at 'scoperef'."""
        citdl = elem.get("citdl")
        if not citdl:
            raise CodeIntelError("no type-inference info for %r" % elem)
        self.log("resolve '%s' type inference for %r:", citdl, elem)
        return self._hit_from_citdl(citdl, scoperef)

    def _hit_from_type_inference(self, citdl, scoperef):
        """Resolve the 'citdl' type inference at 'scoperef'."""
        self.log("resolve '%s' type inference:", citdl)
        return self._hit_from_citdl(citdl, scoperef)

    _built_in_blob = None
    @property
    def built_in_blob(self):
        if self._built_in_blob is None:
            #XXX Presume last lib is stdlib.
            self._built_in_blob = self.buf.libs[-1].get_blob("*")
        return self._built_in_blob

    def parent_scoperef_from_scoperef(self, scoperef):
        blob, lpath = scoperef
        if lpath:
            parent_lpath = lpath[:-1]
            if parent_lpath:
                elem = self._elem_from_scoperef((blob, parent_lpath))
                if elem.get("ilk") == "class":
                    # Python eval shouldn't consider the class-level
                    # scope as a parent scope when resolving from the
                    # top-level. (test python/cpln/skip_class_scope)
                    parent_lpath = parent_lpath[:-1]
            return (blob, parent_lpath)
        elif blob is self._built_in_blob:
            return None
        else:
            return (self.built_in_blob, [])

    def _elem_from_scoperef(self, scoperef):
        """A scoperef is (<blob>, <lpath>). Return the actual elem in
        the <blob> ciElementTree being referred to.
        """
        elem = scoperef[0]
        for lname in scoperef[1]:
            elem = elem.names[lname]
        return elem

