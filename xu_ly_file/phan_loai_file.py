class phan_loai_file:
    ho_tro = {
        'text': ['.txt', '.md', '.log', '.rtf'],
        'config': ['.yml', '.yaml', '.json', '.xml', '.conf', '.cfg', '.ini', '.properties'],
        'document': ['.docx', '.doc', '.pdf', '.odt'],
        'code': ['.py', '.js', '.java', '.cpp', '.c', '.html', '.css', '.php', '.rb', '.go'],
        'subtitle': ['.srt', '.ass', '.ssa', '.sub', '.vtt'],
        'lang': ['.lang', '.po', '.pot', '.xliff'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    }

    def lay_loai(self, ten_file: str) -> str | None:
        ten = ten_file.lower()
        for loai, ds in self.ho_tro.items():
            if any(ten.endswith(ext) for ext in ds):
                return loai
        return None

    def ho_tro_khong(self, ten_file: str) -> bool:
        return self.lay_loai(ten_file) is not None
