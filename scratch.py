from typing import List, Optional
import requests


class ParserError(Exception):
    pass


def rss_parser(url: str, limit: Optional[int] = None) -> List[str]:
    """
    RSS parser.

    Args:
        url: URl to feed
        limit: Number of the items to return. if None, returns all

    Returns:
        json formatted string
    """

    def decode_str(string: str) -> str:
        """
        Replace special symbols in RSS feed
        """
        return string.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

    def split_by_tag_single(data: str, tag: str) -> Optional[str]:
        """
        Fetch string segment between opening and closing tags (first appearance)
        """
        start = data.find(f'<{tag}>')
        if start < 0:  # tag not found
            return None
        end = data.find(f'</{tag}>')
        if end < start:  # closing tag not found
            raise ParserError(f'Closing Tag not found for tag={tag}, data={data}')
        return data[start + len(tag) + 2:end]

    def split_by_tag_multi(data: str, tag: str) -> Optional[List[str]]:
        """
        Fetch string segments between opening and closing tags (all appearances)
        """
        res = data.split(f'<{tag}>')  # each element contains data segment starting with tag
        if len(res) < 2:  # len(res) == 1 means tag not found
            return None
        for i in range(1, len(res)):  # trying to find closing tag for each segment
            end = res[i].find(f'</{tag}>')
            if end > 0:
                res[i] = res[i][:end]  # if found - splitting segment correspondingly
            else:
                raise ParserError(f'Closing Tag not found for tag={tag}, data={res[i]}')  # closing tag not found
        return res[1:]

    def split_by_tags(data: str, tags: List[str], preserve_order=True) -> dict:
        """
        Returns dict where keys=tags and values=corresponding data segments
        Assuming each tag appears only once
        """
        res = dict()
        for tag in tags:
            tag_data = split_by_tag_single(data, tag)
            if tag_data:  # if tag found
                res[tag] = decode_str(tag_data)
        return res

    def parse(data: str, tags_for_channel: List[str], tags_for_item: List[str], limit: int) -> List[dict]:
        """
        Returns list of dicts where each dict contains channel data (tag: data)
        For items data is nested list of dicts with same structure
        """
        channels = split_by_tag_multi(data, 'channel')  # split data into channels
        if not channels:
            raise ParserError('No channels found in data provided')

        res = list()
        for channel in channels:
            channel_data = split_by_tags(channel, tags_for_channel)  # fetch all tags except for "items"
            if channel_data:
                res.append(channel_data)
            else:  # nothing found means channel doesnt have title and description
                raise ParserError(f'Channel title not found, channel={channel}')

            items = split_by_tag_multi(channel, 'item')  # fetch all items as list of strings
            if items:
                if limit is not None:
                    items = items[:limit]
                res[-1]['items'] = list()
                for item in items:
                    item_data = split_by_tags(item, tags_for_item)  # for each item fetch all tags
                    if item_data:
                        res[-1]['items'].append(item_data)
        return res

    def as_json(data: List[dict]) -> List[str]:
        """
        Converts parse result into json-like list of strings
        """
        res = list()
        for channel in data:
            res.append('{')
            for tag in channel.keys():
                if tag != 'items':
                    res.append(f'  "{tag}": "{channel[tag]}",')  # channel properties
            if not channel.get('items'):  # if channel is empty
                res.append('},')
                break

            res.append(f'  "items": [')  # list of items
            for item in channel['items']:
                res.append('    {')
                for tag in item.keys():
                    res.append(f'      "{tag}": "{item[tag]}",')  # item
                res[-1] = res[-1][:-1]  # remove comma in the end
                res.append('    },')
            res[-1] = res[-1][:-1]  # remove comma in the end of the items list
            res.append(f'  ]')
            res.append('},')
        res[-1] = res[-1][:-1]  # remove comma in the end
        return res

    # keys - tags to parse, values - corresponding names for fancy formatting
    tags_for_channel = {'title': 'Feed: ',
                        'link': 'Link: ',
                        'description': 'Description: ',
                        'lastBuildDate': 'Last Build Date: ',
                        'pubDate': 'Publish Date: ',
                        'language': 'Language: ',
                        'category': 'Categories: ',
                        'managinEditor': 'Editor: '}

    # keys - tags to parse, values - corresponding names for fancy formatting
    tags_for_item = {'title': 'Title: ',
                     'author': 'Author: ',
                     'pubDate': 'Published: ',
                     'link': 'Link: ',
                     'category': 'Categories: ',
                     'description': ''}
    xml = requests.get(url).text
    res = parse(xml, list(tags_for_channel.keys()), list(tags_for_item.keys()), limit)  # parse
    res = as_json(res)  # convert to json-like format
    return res


###TEST###
if __name__ == "__main__":
    print("\n".join(rss_parser('https://news.yahoo.com/rss')))
