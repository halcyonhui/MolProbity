<?php # (jEdit options) :folding=explicit:collapseFolds=1:
/*****************************************************************************
    Launches a page to view a syntax-highlighted kinemage as HTML.

INPUTS (via Get or Post):
    file            absolute path of the kinemage file to load

*****************************************************************************/
// EVERY *top-level* page must start this way:
// 1. Define it's relationship to the root of the MolProbity installation.
// Pages in subdirectories of lib/ or public_html/ will need more "/.." 's.
    if(!defined('MP_BASE_DIR')) define('MP_BASE_DIR', realpath(dirname(__FILE__).'/..'));
// 2. Include core functionality - defines constants, etc.
    require_once(MP_BASE_DIR.'/lib/core.php');
// 3. Restore session data. If you don't want to access the session
// data for some reason, you must call mpInitEnvirons() instead.
    mpStartSession();
// 4. For pages that want to see the session but not change it, such as
// pages that are refreshing periodically to monitor a background job.
    mpSessReadOnly();

#{{{ a_function_definition - sumary_statement_goes_here
############################################################################
/**
* Documentation for this function.
*/
//function someFunctionName() {}
#}}}########################################################################

# MAIN - the beginning of execution for this page
############################################################################
// Start the page: produces <HTML>, <HEAD>, <BODY> tags
$file = $_REQUEST['file'];
$name = basename($file);
echo mpPageHeader("Viewing $name");
passthru("java -cp ".MP_BASE_DIR."/public_html/king.jar king.core.KinfileTokenizer -css < $file");
echo mpPageFooter();
?>
