MODULE MoveCircTest
  CONST robtarget pCirStart := [[500,0,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget pCirPoint := [[550,50,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget pCirEnd := [[600,0,400],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];

  PROC main()
    MoveJ pCirStart, v1000, z50, tool0;
    MoveC pCirPoint, pCirEnd, v200, z10, tool0;
  ENDPROC
ENDMODULE
