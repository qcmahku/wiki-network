#!/usr/bin/env python

##########################################################################
#                                                                        #
#  This program is free software; you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation; version 2 of the License.               #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
#                                                                        #
##########################################################################

from bz2 import BZ2File

## LXML
from lxml import etree

## PROJECT LIBS
from sonet.edgecache import EdgeCache
import sonet.mediawiki as mwlib
from sonet.mediawiki import PageProcessor
from sonet import lib

class CurrentPageProcessor(PageProcessor):
    def process(self, elem):
        tag = self.tag
        user = None
        for child in elem:
            if child.tag == tag['title'] and child.text:
                a_title = child.text.split('/')[0].split(':')

                if len(a_title) > 1 and a_title[0] in self.user_talk_names:
                    user = a_title[1]
                else:
                    return
            elif child.tag == tag['revision']:
                for rc in child:
                    if rc.tag != tag['text']:
                        continue

                    assert user, "User still not defined"
                    if not (rc.text and user):
                        continue

                    if (mwlib.isHardRedirect(rc.text) or
                       mwlib.isSoftRedirect(rc.text)):
                        continue

                    #try:
                    #talks = mwlib.getCollaborators(rc.text, self.search)
                    talks = mwlib.getCollaborators(rc.text, ('User', 'Utente'),
                                                   lang="vec")
                    #except:
                    #    print "Warning: exception with user %s" % (
                    #        user.encode('utf-8'),)

                    self.ecache.add(mwlib.capfirst(user.replace('_', ' ')),
                                    talks)
                    self.count += 1
                    if not self.count % 500:
                        print self.count


def main():
    import optparse

    p = optparse.OptionParser(usage="usage: %prog file")
    p.add_option('-v', action="store_true", dest="verbose", default=False,
                 help="Verbose output (like timings)")
    opts, files = p.parse_args()
    if opts.verbose:
        import sys, logging
        logging.basicConfig(stream=sys.stderr,
                            level=logging.DEBUG)

    if len(files) != 1:
        p.error("Give me one file, please")
    xml = files[0]

    en_user, en_user_talk = u"User", u"User talk"

    lang, date, type_ = mwlib.explode_dump_filename(xml)

    ecache = EdgeCache()

    src = BZ2File(xml)

    tag = mwlib.getTags(src)

    ns_translation = mwlib.getTranslations(src)
    lang_user, lang_user_talk = ns_translation['User'], \
             ns_translation['User talk']

    assert lang_user, "User namespace not found"
    assert lang_user_talk, "User Talk namespace not found"

    lang_user = unicode(lang_user)
    en_user = unicode(en_user)

    _fast = True
    if _fast:
        src.close()
        src = lib.SevenZipFileExt(xml)

    processor = CurrentPageProcessor(ecache=ecache, tag=tag,
                              user_talk_names=(lang_user_talk, en_user_talk),
                              search=(lang_user, en_user), lang=lang)
    mwlib.fast_iter(etree.iterparse(src, tag=tag['page'], strip_cdata=False),
                    processor.process)

    ecache.flush()
    g = ecache.get_network()

    print "Len:", len(g.vs)
    print "Edges:", len(g.es)

    g.write("%swiki-%s%s.pickle" % (lang, date, type_), format="pickle")


if __name__ == "__main__":
    #import cProfile as profile
    #profile.run('main()', 'mainprof')
    main()