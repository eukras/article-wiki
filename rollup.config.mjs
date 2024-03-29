import {nodeResolve} from '@rollup/plugin-node-resolve';

export default {
	input: 'src/main.js',
	output: {
        name: 'ArticleWiki',
		file: 'dist/bundle.js',
		format: 'iife'
	},
    plugins: [nodeResolve()]
};
